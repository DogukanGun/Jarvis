// @ts-nocheck — see agent.ts.
import type { FastifyInstance } from 'fastify'
import { z } from 'zod'
import {
  PublicKey,
  LAMPORTS_PER_SOL,
  VersionedTransaction,
  Transaction,
  TransactionMessage,
  type AddressLookupTableAccount,
  type Connection,
} from '@solana/web3.js'
import type { AgentBundle } from './agent.js'
import type { TraderConfig } from './config.js'
import { LoopbackWallet, type SignClaim } from './wallet-adapter.js'

const swapSchema = z.object({
  outputMint: z.string(),
  amount: z.number().positive(),
  inputMint: z.string().optional(),
  slippageBps: z.number().int().min(1).max(10000).optional(),
  policyId: z.string().min(8),
  lamportsOut: z.number().int().positive(),
})

const signAndSendSchema = z.object({
  policyId: z.string().min(8),
  tx: z.string().min(8),
  action: z.enum(['swap', 'transfer', 'pumpfun_buy', 'pumpfun_sell']),
  lamportsOut: z.number().int().positive(),
  mint: z.string().optional(),
})

// Refresh the recentBlockhash of an unsigned tx so it doesn't expire mid-flight.
// Solana's blockhash window is ~150 slots (~1 minute); PumpPortal builds with
// a blockhash that's already several seconds old by the time it returns to
// us, and adding network hops + signing round-trip easily blows past the
// validator's freshness check. We decompile the message, swap the blockhash,
// recompile, and return the new (still-unsigned) tx.
async function refreshBlockhash(
  unsigned: VersionedTransaction | Transaction,
  conn: Connection,
): Promise<VersionedTransaction | Transaction> {
  const { blockhash } = await conn.getLatestBlockhash('confirmed')

  if (unsigned instanceof Transaction) {
    unsigned.recentBlockhash = blockhash
    // Drop any pre-existing signatures since the message hash just changed.
    unsigned.signatures = unsigned.signatures.map((s) => ({ ...s, signature: null }))
    return unsigned
  }

  // VersionedTransaction → decompile, mutate, recompile (handles ALT lookups).
  const lookups = await Promise.all(
    unsigned.message.addressTableLookups.map(async (l) => {
      const r = await conn.getAddressLookupTable(l.accountKey)
      return r.value
    }),
  )
  const validLookups = lookups.filter((l): l is AddressLookupTableAccount => l !== null)
  const decompiled = TransactionMessage.decompile(unsigned.message, {
    addressLookupTableAccounts: validLookups,
  })
  decompiled.recentBlockhash = blockhash
  const newMsg = decompiled.compileToV0Message(validLookups)
  return new VersionedTransaction(newMsg)
}

function deserialize(b64: string): VersionedTransaction | Transaction {
  const buf = Buffer.from(b64, 'base64')
  try {
    return VersionedTransaction.deserialize(new Uint8Array(buf))
  } catch {
    return Transaction.from(buf)
  }
}

function serialize(tx: VersionedTransaction | Transaction): string {
  if (tx instanceof VersionedTransaction) {
    return Buffer.from(tx.serialize()).toString('base64')
  }
  return Buffer.from(tx.serialize({ requireAllSignatures: false, verifySignatures: false }))
    .toString('base64')
}

export function registerAutoRoutes(app: FastifyInstance, cfg: TraderConfig, bundle: AgentBundle): void {
  app.post('/api/auto/swap', async (req, reply) => {
    const parsed = swapSchema.safeParse(req.body)
    if (!parsed.success) return reply.code(400).send({ error: parsed.error.flatten() })
    const { outputMint, amount, inputMint, slippageBps, policyId, lamportsOut } = parsed.data
    const claim: SignClaim = { action: 'swap', lamportsOut, mint: outputMint }

    const { agent, wallet } = bundle.buildAutoAgent(policyId)
    try {
      const sig = await wallet.withClaim(claim, () =>
        agent.methods.trade(
          new PublicKey(outputMint),
          amount,
          inputMint ? new PublicKey(inputMint) : undefined,
          slippageBps,
        ),
      )
      return { signature: sig }
    } catch (err) {
      req.log.error({ err }, 'auto swap failed')
      return reply.code(500).send({ error: (err as Error).message })
    }
  })

  app.post('/api/auto/sign-and-send', async (req, reply) => {
    const parsed = signAndSendSchema.safeParse(req.body)
    if (!parsed.success) return reply.code(400).send({ error: parsed.error.flatten() })
    const { policyId, tx, action, lamportsOut, mint } = parsed.data

    const conn = bundle.manualAgent.connection
    const wallet = new LoopbackWallet(cfg, policyId)
    try {
      // 1. Decode the unsigned tx coming from the strategy.
      const unsigned = deserialize(tx)
      // 2. Replace its blockhash with a fresh one so the validator doesn't
      //    reject as stale. Critical for PumpPortal txs which can be ~10s
      //    old by the time they reach us.
      const refreshed = await refreshBlockhash(unsigned, conn)
      const refreshedB64 = serialize(refreshed)
      // 3. Sign via the Electron loopback under the active session policy.
      const signedB64 = await wallet.signAndSendUnsigned(refreshedB64, { action, lamportsOut, mint })
      const signedBuf = Buffer.from(signedB64, 'base64')
      // 4. Broadcast. skipPreflight=true because we trust the signing path
      //    and the cluster's leader will simulate again anyway.
      const sig = await conn.sendRawTransaction(new Uint8Array(signedBuf), {
        skipPreflight: true,
        maxRetries: 3,
      })
      const latest = await conn.getLatestBlockhash('confirmed')
      await conn.confirmTransaction(
        { signature: sig, blockhash: latest.blockhash, lastValidBlockHeight: latest.lastValidBlockHeight },
        'confirmed',
      )
      return { signature: sig }
    } catch (err) {
      req.log.error({ err }, 'sign-and-send failed')
      return reply.code(500).send({ error: (err as Error).message })
    }
  })

  app.get('/api/auto/echo', async () => ({
    ok: true,
    network: cfg.network,
    publicKey: cfg.publicKey,
    lamportsPerSol: LAMPORTS_PER_SOL,
  }))
}
