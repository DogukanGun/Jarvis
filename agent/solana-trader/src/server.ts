// @ts-nocheck — see note in agent.ts: SAK method signatures don't match
// their published types post-plugin-binding. Runtime behaviour is correct.
import Fastify from 'fastify'
import cors from '@fastify/cors'
import { z } from 'zod'
import { PublicKey, LAMPORTS_PER_SOL } from '@solana/web3.js'
import { loadConfig } from './config.js'
import { buildAgentBundle } from './agent.js'
import { registerAutoRoutes } from './auto-routes.js'

const cfg = loadConfig()
const bundle = buildAgentBundle(cfg)
const agent = bundle.manualAgent

const app = Fastify({ logger: { level: 'info' } })
await app.register(cors, { origin: true })
registerAutoRoutes(app, cfg, bundle)

app.get('/health', async () => ({
  ok: true,
  publicKey: cfg.publicKey,
  network: cfg.network,
  rpcUrl: cfg.rpcUrl,
}))

// ── Balance & portfolio ───────────────────────────────────────────────────────
app.get('/api/balance', async () => {
  const sol = await agent.connection.getBalance(new PublicKey(cfg.publicKey))
  return {
    publicKey: cfg.publicKey,
    sol: sol / LAMPORTS_PER_SOL,
    lamports: sol,
    network: cfg.network,
  }
})

// ── Jupiter swap ──────────────────────────────────────────────────────────────
const swapSchema = z.object({
  outputMint: z.string(),
  amount: z.number().positive(),
  inputMint: z.string().optional(),
  slippageBps: z.number().int().min(1).max(10000).optional(),
})

app.post('/api/swap', async (req, reply) => {
  const parsed = swapSchema.safeParse(req.body)
  if (!parsed.success) return reply.code(400).send({ error: parsed.error.flatten() })
  const { outputMint, amount, inputMint, slippageBps } = parsed.data
  try {
    // SAK plugin-token exposes `trade(target, amount, source?, slippage?)`.
    // signature: trade(targetMint, amount, sourceMint?, slippageBps?)
    const sig = await agent.methods.trade(
      new PublicKey(outputMint),
      amount,
      inputMint ? new PublicKey(inputMint) : undefined,
      slippageBps,
    )
    return { signature: sig }
  } catch (err) {
    req.log.error({ err }, 'swap failed')
    return reply.code(500).send({ error: (err as Error).message })
  }
})

// ── Jupiter price quote (read-only) ───────────────────────────────────────────
const priceSchema = z.object({ token: z.string() })

app.post('/api/price', async (req, reply) => {
  const parsed = priceSchema.safeParse(req.body)
  if (!parsed.success) return reply.code(400).send({ error: parsed.error.flatten() })
  try {
    const price = await agent.methods.fetchPrice(new PublicKey(parsed.data.token))
    return { price }
  } catch (err) {
    return reply.code(500).send({ error: (err as Error).message })
  }
})

// ── Token info via Dexscreener (read-only) ────────────────────────────────────
const tokenInfoSchema = z.object({ mint: z.string() })

app.post('/api/token-info', async (req, reply) => {
  const parsed = tokenInfoSchema.safeParse(req.body)
  if (!parsed.success) return reply.code(400).send({ error: parsed.error.flatten() })
  try {
    const info = await agent.methods.getTokenDataByAddress(parsed.data.mint)
    return { info }
  } catch (err) {
    return reply.code(500).send({ error: (err as Error).message })
  }
})

// ── Transfer (SOL or SPL) ─────────────────────────────────────────────────────
const transferSchema = z.object({
  to: z.string(),
  amount: z.number().positive(),
  mint: z.string().optional(),
})

app.post('/api/transfer', async (req, reply) => {
  const parsed = transferSchema.safeParse(req.body)
  if (!parsed.success) return reply.code(400).send({ error: parsed.error.flatten() })
  const { to, amount, mint } = parsed.data
  try {
    const sig = await agent.methods.transfer(
      new PublicKey(to),
      amount,
      mint ? new PublicKey(mint) : undefined,
    )
    return { signature: sig }
  } catch (err) {
    return reply.code(500).send({ error: (err as Error).message })
  }
})

// ── Pump.fun token launch (creator side) ──────────────────────────────────────
const launchSchema = z.object({
  tokenName: z.string().min(1).max(32),
  tokenTicker: z.string().min(1).max(10),
  description: z.string(),
  imageUrl: z.string().url(),
  initialLiquiditySOL: z.number().positive().optional(),
  twitter: z.string().optional(),
  telegram: z.string().optional(),
  website: z.string().optional(),
})

app.post('/api/pumpfun/launch', async (req, reply) => {
  const parsed = launchSchema.safeParse(req.body)
  if (!parsed.success) return reply.code(400).send({ error: parsed.error.flatten() })
  const { tokenName, tokenTicker, description, imageUrl, ...rest } = parsed.data
  try {
    const result = await agent.methods.launchPumpFunToken(
      tokenName,
      tokenTicker,
      description,
      imageUrl,
      rest,
    )
    return { result }
  } catch (err) {
    return reply.code(500).send({ error: (err as Error).message })
  }
})

// ── Execute a TradeIntent emitted by solana-strategy ──────────────────────────
const intentSchema = z.object({
  action: z.enum(['swap', 'transfer']),
  params: z.record(z.unknown()),
  sourceAgent: z.string().optional(),
})

app.post('/api/execute-intent', async (req, reply) => {
  const parsed = intentSchema.safeParse(req.body)
  if (!parsed.success) return reply.code(400).send({ error: parsed.error.flatten() })
  const { action, params } = parsed.data
  try {
    if (action === 'swap') {
      const p = swapSchema.parse(params)
      const sig = await agent.methods.trade(
        new PublicKey(p.outputMint),
        p.amount,
        p.inputMint ? new PublicKey(p.inputMint) : undefined,
        p.slippageBps,
      )
      return { signature: sig, action }
    }
    if (action === 'transfer') {
      const p = transferSchema.parse(params)
      const sig = await agent.methods.transfer(
        new PublicKey(p.to),
        p.amount,
        p.mint ? new PublicKey(p.mint) : undefined,
      )
      return { signature: sig, action }
    }
    return reply.code(400).send({ error: 'unknown action' })
  } catch (err) {
    return reply.code(500).send({ error: (err as Error).message })
  }
})

const start = async (): Promise<void> => {
  try {
    await app.listen({ port: cfg.port, host: '127.0.0.1' })
    app.log.info({ port: cfg.port, network: cfg.network, publicKey: cfg.publicKey }, 'solana-trader ready')
  } catch (err) {
    app.log.error({ err }, 'failed to start')
    process.exit(1)
  }
}

void start()

// Graceful shutdown when Electron kills us
for (const sig of ['SIGTERM', 'SIGINT']) {
  process.on(sig, () => {
    app.log.info({ sig }, 'shutting down')
    app.close().finally(() => process.exit(0))
  })
}
