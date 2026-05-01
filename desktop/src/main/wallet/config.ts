import { app } from 'electron'
import { join } from 'path'
import { existsSync, readFileSync, writeFileSync } from 'fs'

export type Network = 'mainnet' | 'devnet'

export interface WalletConfig {
  network: Network
  rpcUrl: string
  explorerBase: string
  autoLockSeconds: number
}

const DEFAULTS: Record<Network, { rpcUrl: string; explorerBase: string }> = {
  mainnet: {
    rpcUrl: 'https://api.mainnet-beta.solana.com',
    explorerBase: 'https://solscan.io',
  },
  devnet: {
    rpcUrl: 'https://api.devnet.solana.com',
    explorerBase: 'https://solscan.io/?cluster=devnet',
  },
}

const DEFAULT_CONFIG: WalletConfig = {
  network: 'devnet',
  rpcUrl: DEFAULTS.devnet.rpcUrl,
  explorerBase: DEFAULTS.devnet.explorerBase,
  // 30 minutes — long enough to avoid surprise auto-locks during a demo,
  // short enough that an unattended laptop doesn't sit unlocked overnight.
  autoLockSeconds: 1800,
}

function configPath(): string {
  return join(app.getPath('userData'), 'wallet-config.json')
}

// Anything shorter than this triggered surprise auto-locks during demos
// and SIGTERM'd the spawned trader/strategy children. Floor old configs
// to a sensible value on read.
const MIN_AUTO_LOCK_SECONDS = 600

export function loadConfig(): WalletConfig {
  try {
    if (!existsSync(configPath())) return { ...DEFAULT_CONFIG }
    const raw = readFileSync(configPath(), 'utf-8')
    const parsed = JSON.parse(raw) as Partial<WalletConfig>
    const network = parsed.network === 'mainnet' ? 'mainnet' : 'devnet'
    let autoLockSeconds =
      typeof parsed.autoLockSeconds === 'number' ? parsed.autoLockSeconds : DEFAULT_CONFIG.autoLockSeconds
    if (autoLockSeconds > 0 && autoLockSeconds < MIN_AUTO_LOCK_SECONDS) {
      autoLockSeconds = DEFAULT_CONFIG.autoLockSeconds
    }
    return {
      network,
      rpcUrl: parsed.rpcUrl ?? DEFAULTS[network].rpcUrl,
      explorerBase: parsed.explorerBase ?? DEFAULTS[network].explorerBase,
      autoLockSeconds,
    }
  } catch {
    return { ...DEFAULT_CONFIG }
  }
}

export function saveConfig(patch: Partial<WalletConfig>): WalletConfig {
  const current = loadConfig()
  const merged: WalletConfig = { ...current, ...patch }

  // If network changed and the caller didn't override the RPC/explorer, snap to defaults.
  if (patch.network && !patch.rpcUrl) merged.rpcUrl = DEFAULTS[patch.network].rpcUrl
  if (patch.network && !patch.explorerBase) merged.explorerBase = DEFAULTS[patch.network].explorerBase

  writeFileSync(configPath(), JSON.stringify(merged, null, 2), { mode: 0o600 })
  return merged
}
