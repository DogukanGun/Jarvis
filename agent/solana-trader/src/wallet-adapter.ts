import {
  PublicKey,
  Transaction,
  VersionedTransaction,
} from '@solana/web3.js'
import type { TraderConfig } from './config.js'

export interface SignClaim {
  action: 'swap' | 'transfer' | 'pumpfun_buy' | 'pumpfun_sell'
  lamportsOut: number
  mint?: string
}

// Implements the SAK BaseWallet interface by proxying every signing request
// to the Electron loopback signer. The keypair never leaves the Electron
// main process. Two flavours coexist in one trader process:
//   - manualWallet  (no policy header) — Trade-page tabs, biometric per-call.
//   - autoWallet    (has policy header)  — auto-trade routes, session-gated.
export class LoopbackWallet {
  public readonly publicKey: PublicKey
  private readonly url: string
  private readonly token: string
  private readonly policyId: string | null
  private pendingClaim: SignClaim | null = null
  private pendingClaims: SignClaim[] | null = null

  constructor(cfg: TraderConfig, policyId: string | null = null) {
    this.publicKey = new PublicKey(cfg.publicKey)
    this.url = `http://127.0.0.1:${cfg.loopbackPort}`
    this.token = cfg.loopbackToken
    this.policyId = policyId
  }

  /** Run a SAK call with a per-call claim attached to the next sign request. */
  async withClaim<R>(claim: SignClaim, fn: () => Promise<R>): Promise<R> {
    if (!this.policyId) throw new Error('withClaim requires a policy-bound wallet')
    this.pendingClaim = claim
    try { return await fn() }
    finally { this.pendingClaim = null }
  }

  /** Same but for batch signing — claims must align with the txs array. */
  async withClaims<R>(claims: SignClaim[], fn: () => Promise<R>): Promise<R> {
    if (!this.policyId) throw new Error('withClaims requires a policy-bound wallet')
    this.pendingClaims = claims
    try { return await fn() }
    finally { this.pendingClaims = null }
  }

  private headers(): Record<string, string> {
    const h: Record<string, string> = {
      'content-type': 'application/json',
      'authorization': `Bearer ${this.token}`,
    }
    if (this.policyId) h['x-jarvis-policy-id'] = this.policyId
    return h
  }

  private static serialize(tx: Transaction | VersionedTransaction): string {
    if (tx instanceof VersionedTransaction) {
      return Buffer.from(tx.serialize()).toString('base64')
    }
    return Buffer.from(tx.serialize({ requireAllSignatures: false, verifySignatures: false })).toString('base64')
  }

  private static deserialize<T extends Transaction | VersionedTransaction>(
    b64: string,
    template: T,
  ): T {
    const buf = Buffer.from(b64, 'base64')
    if (template instanceof VersionedTransaction) {
      return VersionedTransaction.deserialize(new Uint8Array(buf)) as T
    }
    return Transaction.from(buf) as T
  }

  async signTransaction<T extends Transaction | VersionedTransaction>(tx: T): Promise<T> {
    const body: Record<string, unknown> = { tx: LoopbackWallet.serialize(tx) }
    if (this.policyId) {
      if (!this.pendingClaim) {
        throw new Error('auto-mode sign called without a pending claim — use withClaim()')
      }
      body.claim = this.pendingClaim
    }
    const res = await fetch(`${this.url}/sign-tx`, {
      method: 'POST',
      headers: this.headers(),
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const text = await res.text()
      throw new Error(`Loopback sign failed (${res.status}): ${text}`)
    }
    const { tx: signed } = (await res.json()) as { tx: string }
    return LoopbackWallet.deserialize(signed, tx)
  }

  async signAllTransactions<T extends Transaction | VersionedTransaction>(txs: T[]): Promise<T[]> {
    if (txs.length === 0) return txs
    const body: Record<string, unknown> = {
      txs: txs.map((t) => LoopbackWallet.serialize(t)),
    }
    if (this.policyId) {
      if (!this.pendingClaims || this.pendingClaims.length !== txs.length) {
        throw new Error('auto-mode signAll called without aligned claims — use withClaims()')
      }
      body.claims = this.pendingClaims
    }
    const res = await fetch(`${this.url}/sign-all-tx`, {
      method: 'POST',
      headers: this.headers(),
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const text = await res.text()
      throw new Error(`Loopback sign-all failed (${res.status}): ${text}`)
    }
    const { txs: signed } = (await res.json()) as { txs: string[] }
    return signed.map((b64, i) => LoopbackWallet.deserialize(b64, txs[i]))
  }

  /** For pre-built unsigned txs delivered to /api/auto/sign-and-send. */
  async signAndSendUnsigned(unsignedB64: string, claim: SignClaim): Promise<string> {
    if (!this.policyId) throw new Error('signAndSendUnsigned requires a policy-bound wallet')
    const res = await fetch(`${this.url}/sign-tx`, {
      method: 'POST',
      headers: this.headers(),
      body: JSON.stringify({ tx: unsignedB64, claim }),
    })
    if (!res.ok) {
      const text = await res.text()
      throw new Error(`Loopback sign failed (${res.status}): ${text}`)
    }
    const { tx: signedB64 } = (await res.json()) as { tx: string }
    return signedB64
  }
}
