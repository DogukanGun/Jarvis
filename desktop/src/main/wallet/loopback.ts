import { createServer, type Server } from 'http'
import { randomBytes } from 'crypto'
import { Transaction, VersionedTransaction } from '@solana/web3.js'
import { isUnlocked, getPublicKey, signTransaction, onLockChange } from './signer'
import { safeCompare } from './vault'
import { loadConfig } from './config'
import {
  validateClaim,
  recordSpend,
  getActiveSession,
  type SignClaim,
} from './session'

let server: Server | null = null
let token: string | null = null
let port: number | null = null

function readBody(req: import('http').IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = []
    req.on('data', (c) => chunks.push(c))
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf-8')))
    req.on('error', reject)
  })
}

function reply(res: import('http').ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { 'content-type': 'application/json' })
  res.end(JSON.stringify(body))
}

function authOk(req: import('http').IncomingMessage): boolean {
  if (!token) return false
  const header = req.headers['authorization']
  if (!header || typeof header !== 'string' || !header.startsWith('Bearer ')) return false
  return safeCompare(header.slice(7), token)
}

function deserializeTx(b64: string): Transaction | VersionedTransaction {
  const buf = Buffer.from(b64, 'base64')
  // Try versioned first; fallback to legacy.
  try {
    return VersionedTransaction.deserialize(new Uint8Array(buf))
  } catch {
    return Transaction.from(buf)
  }
}

function serializeTx(tx: Transaction | VersionedTransaction): string {
  if (tx instanceof VersionedTransaction) {
    return Buffer.from(tx.serialize()).toString('base64')
  }
  return Buffer.from(tx.serialize({ requireAllSignatures: false })).toString('base64')
}

export interface LoopbackInfo {
  port: number
  token: string
  publicKey: string
  rpcUrl: string
  network: 'mainnet' | 'devnet'
}

export async function startLoopback(): Promise<LoopbackInfo> {
  if (server) return getLoopbackInfo()
  if (!isUnlocked()) throw new Error('Wallet must be unlocked before starting loopback')

  token = randomBytes(32).toString('base64url')

  server = createServer(async (req, res) => {
    try {
      if (!authOk(req)) {
        reply(res, 401, { error: 'unauthorized' })
        return
      }
      const url = req.url ?? '/'
      if (req.method === 'GET' && url === '/pubkey') {
        reply(res, 200, { publicKey: getPublicKey() })
        return
      }
      if (req.method === 'GET' && url === '/health') {
        reply(res, 200, { ok: true, unlocked: isUnlocked() })
        return
      }
      if (req.method === 'POST' && url === '/sign-tx') {
        const body = JSON.parse(await readBody(req)) as {
          tx: string
          claim?: SignClaim
        }
        if (!body?.tx) { reply(res, 400, { error: 'missing tx' }); return }
        if (!isUnlocked()) { reply(res, 423, { error: 'wallet locked' }); return }

        const policyHeader = req.headers['x-jarvis-policy-id']
        if (typeof policyHeader === 'string' && policyHeader.length > 0) {
          // Auto-mode: must satisfy active session policy.
          if (!body.claim) {
            reply(res, 400, { error: 'auto-mode requires `claim` in body' })
            return
          }
          const reason = validateClaim(policyHeader, body.claim)
          if (reason) {
            reply(res, 403, { error: `policy denied: ${reason}` })
            return
          }
          const tx = deserializeTx(body.tx)
          signTransaction(tx)
          recordSpend(body.claim.lamportsOut)
          reply(res, 200, { tx: serializeTx(tx), session: getActiveSession() })
          return
        }

        // Manual path (no header) — preserve existing behavior.
        const tx = deserializeTx(body.tx)
        signTransaction(tx)
        reply(res, 200, { tx: serializeTx(tx) })
        return
      }
      if (req.method === 'POST' && url === '/sign-all-tx') {
        const body = JSON.parse(await readBody(req)) as { txs: string[]; claims?: SignClaim[] }
        if (!Array.isArray(body?.txs)) { reply(res, 400, { error: 'missing txs' }); return }
        if (!isUnlocked()) { reply(res, 423, { error: 'wallet locked' }); return }

        const policyHeader = req.headers['x-jarvis-policy-id']
        if (typeof policyHeader === 'string' && policyHeader.length > 0) {
          if (!Array.isArray(body.claims) || body.claims.length !== body.txs.length) {
            reply(res, 400, { error: 'auto-mode requires `claims[]` matching `txs[]` length' })
            return
          }
          for (const claim of body.claims) {
            const reason = validateClaim(policyHeader, claim)
            if (reason) {
              reply(res, 403, { error: `policy denied: ${reason}` })
              return
            }
          }
          const signed = body.txs.map((t, i) => {
            const tx = deserializeTx(t)
            signTransaction(tx)
            recordSpend(body.claims![i].lamportsOut)
            return serializeTx(tx)
          })
          reply(res, 200, { txs: signed, session: getActiveSession() })
          return
        }

        const signed = body.txs.map((t) => {
          const tx = deserializeTx(t)
          signTransaction(tx)
          return serializeTx(tx)
        })
        reply(res, 200, { txs: signed })
        return
      }
      reply(res, 404, { error: 'not found' })
    } catch (err) {
      reply(res, 500, { error: (err as Error).message })
    }
  })

  await new Promise<void>((resolve, reject) => {
    server!.once('error', reject)
    server!.listen(0, '127.0.0.1', () => resolve())
  })
  const addr = server.address()
  if (!addr || typeof addr === 'string') throw new Error('Failed to bind loopback')
  port = addr.port
  return getLoopbackInfo()
}

export function stopLoopback(): void {
  if (server) {
    try { server.close() } catch { /* ignore */ }
  }
  server = null
  token = null
  port = null
}

export function getLoopbackInfo(): LoopbackInfo {
  if (!server || !token || !port) throw new Error('Loopback not running')
  const cfg = loadConfig()
  return {
    port,
    token,
    publicKey: getPublicKey() ?? '',
    rpcUrl: cfg.rpcUrl,
    network: cfg.network,
  }
}

export function isLoopbackRunning(): boolean {
  return server !== null
}

// Auto-start on unlock. We deliberately do NOT stop on lock: the server
// already gates `/sign-tx` on `isUnlocked()` and returns 423 when locked,
// which is the correct security boundary. Stopping the server would cycle
// the random token + port and force every spawned agent to be restarted on
// each unlock — expensive and unnecessary.
let unsubscribe: (() => void) | null = null
export function bindLoopbackToSigner(): void {
  if (unsubscribe) return
  unsubscribe = onLockChange((unlocked) => {
    if (unlocked) {
      startLoopback().catch((e) => console.warn('Loopback start failed:', e))
    }
  })
}
