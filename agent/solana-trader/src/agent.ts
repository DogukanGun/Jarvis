import { SolanaAgentKit } from 'solana-agent-kit'
import TokenPlugin from '@solana-agent-kit/plugin-token'
import DefiPlugin from '@solana-agent-kit/plugin-defi'
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
    .use(DefiPlugin)
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
