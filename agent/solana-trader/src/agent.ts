// @ts-nocheck — SAK v2 method signatures shifted between releases; we call
// them at runtime correctly but the published .d.ts files don't match what
// the actual `methods` object exposes after plugin.use(). Suppress strict
// type checking here; the JS still emits and runs.
import { SolanaAgentKit } from 'solana-agent-kit'
import TokenPlugin from '@solana-agent-kit/plugin-token'
// NOTE: @solana-agent-kit/plugin-defi pulls in @meteora-ag/dlmm, which uses
// directory imports that Node's strict ESM loader rejects. We don't use any
// DefiPlugin actions in our routes (Jupiter swap + transfer + Pump.fun launch
// all live in plugin-token), so it's safe to drop. Re-add if/when we need
// Drift/Meteora/Raydium and the dlmm package fixes its imports.
import { LoopbackWallet } from './wallet-adapter.js'
import type { TraderConfig } from './config.js'

export type Agent = ReturnType<typeof buildAgent>

export interface AgentBundle {
  manualAgent: ReturnType<typeof buildOne>
  manualWallet: LoopbackWallet
  buildAutoAgent: (policyId: string) => { agent: ReturnType<typeof buildOne>; wallet: LoopbackWallet }
}

function buildOne(wallet: LoopbackWallet, cfg: TraderConfig) {
  return new SolanaAgentKit(wallet, cfg.rpcUrl, {})
    .use(TokenPlugin)
}

export function buildAgent(cfg: TraderConfig) {
  // Backward-compat default export used by existing manual routes.
  const wallet = new LoopbackWallet(cfg)
  return buildOne(wallet, cfg)
}

export function buildAgentBundle(cfg: TraderConfig): AgentBundle {
  const manualWallet = new LoopbackWallet(cfg)
  const manualAgent = buildOne(manualWallet, cfg)
  return {
    manualAgent,
    manualWallet,
    buildAutoAgent: (policyId: string) => {
      const wallet = new LoopbackWallet(cfg, policyId)
      return { agent: buildOne(wallet, cfg), wallet }
    },
  }
}
