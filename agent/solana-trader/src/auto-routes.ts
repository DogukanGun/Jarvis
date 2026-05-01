import type { FastifyInstance } from 'fastify'
import { z } from 'zod'
import { PublicKey, LAMPORTS_PER_SOL } from '@solana/web3.js'
import type { AgentBundle } from './agent.js'
import type { TraderConfig } from './config.js'
import { LoopbackWallet, type SignClaim } from './wallet-adapter.js'

const swapSchema = z.object({
  outputMint: z.string(),
  amount: z.number().positive(),
  inputMint: z.string().optional(),
  slippageBps: z.number().int().min(1).max(10000).optional(),
  policyId: z.string().min(8),
  // Used to enforce the policy gate. The strategy must declare the SOL
  // value of the trade; the loopback verifies this against the active
  // session's max-per-trade and total budget.
  lamportsOut: z.number().int().positive(),
})

const signAndSendSchema = z.object({
  policyId: z.string().min(8),
  tx: z.string().min(8),
  action: z.enum(['swap', 'transfer', 'pumpfun_buy', 'pumpfun_sell']),
  lamportsOut: z.number().int().positive(),
  mint: z.string().optional(),
})

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

    const wallet = new LoopbackWallet(cfg, policyId)
    try {
      const signedB64 = await wallet.signAndSendUnsigned(tx, { action, lamportsOut, mint })
      const buf = Buffer.from(signedB64, 'base64')
      const conn = bundle.manualAgent.connection
      const sig = await conn.sendRawTransaction(new Uint8Array(buf), { skipPreflight: false, maxRetries: 3 })
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
