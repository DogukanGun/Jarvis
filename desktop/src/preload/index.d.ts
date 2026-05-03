import { ElectronAPI } from '@electron-toolkit/preload'

export type Network = 'mainnet' | 'devnet'

export type CreateMode =
  | { kind: 'generate' }
  | { kind: 'mnemonic'; mnemonic: string }
  | { kind: 'base58'; base58: string }

export interface WalletConfig {
  network: Network
  rpcUrl: string
  explorerBase: string
  autoLockSeconds: number
}

export interface TokenHolding {
  mint: string
  amount: string
  uiAmount: number
  decimals: number
  tokenAccount: string
  programId: string
}

export interface SolBalance {
  lamports: number
  sol: number
}

export interface WalletStatus {
  hasVault: boolean
  isUnlocked: boolean
  publicKey: string | null
  config: WalletConfig
}

export type SpawnState = 'not-installed' | 'spawning' | 'running' | 'crashed' | 'stopped'

export interface AgentStatus {
  name: 'solana-trader' | 'solana-strategy' | 'legal-rag'
  state: SpawnState
  port: number
  pid: number | null
  logPath: string
  logTail: string[]
  lastError: string | null
}

export type AgentSnapshot = { trader: AgentStatus; strategy: AgentStatus; legalRag: AgentStatus }

export interface AgentsApi {
  status: () => Promise<AgentSnapshot>
  installTrader: () => Promise<{ ok: boolean; code: number | null }>
  installStrategy: () => Promise<{ ok: boolean; code: number | null }>
  installLegalRag: () => Promise<{ ok: boolean; code: number | null }>
  restartTrader: () => Promise<AgentSnapshot>
  restartStrategy: () => Promise<AgentSnapshot>
  restartLegalRag: () => Promise<AgentSnapshot>
  startAll: () => Promise<AgentSnapshot>
  onStatusChange: (callback: (snapshot: AgentSnapshot) => void) => () => void
  onInstallLog: (callback: (line: string) => void) => () => void
}

export type AutoStrategy = 'indicator' | 'copy_trade' | 'pumpfun_snipe'
export type AutoAction = 'swap' | 'transfer' | 'pumpfun_buy' | 'pumpfun_sell'

export interface SessionPolicyInput {
  strategy: AutoStrategy
  maxTradeSol: number
  totalBudgetSol: number
  durationSec: number
  allowedActions: AutoAction[]
  allowedMints?: string[]
}

export interface SessionPolicy {
  id: string
  strategy: AutoStrategy
  maxTradeSol: number
  totalBudgetSol: number
  spentSol: number
  expiresAt: number
  startedAt: number
  allowedActions: AutoAction[]
  allowedMints?: string[]
}

export interface WalletSessionApi {
  start: (input: SessionPolicyInput) => Promise<SessionPolicy>
  status: () => Promise<SessionPolicy | null>
  end: () => Promise<boolean>
  onChange: (callback: (s: SessionPolicy | null) => void) => () => void
}

export interface WalletApi {
  status: () => Promise<WalletStatus>
  create: (mode: CreateMode, pin: string) => Promise<{ publicKey: string; mnemonic: string | null }>
  wipe: () => Promise<boolean>
  unlock: (pin: string) => Promise<{ ok: boolean; publicKey?: string; error?: string }>
  verifyPin: (pin: string) => Promise<boolean>
  exportPrivateKey: (
    pin: string,
  ) => Promise<{ ok: boolean; base58?: string; array?: number[]; error?: string }>
  lock: () => Promise<boolean>
  getConfig: () => Promise<WalletConfig>
  setConfig: (patch: Partial<WalletConfig>) => Promise<WalletConfig>
  getBalance: () => Promise<{
    publicKey: string
    sol: SolBalance
    holdings: TokenHolding[]
    network: Network
  }>
  airdrop: (
    sol: number,
  ) => Promise<{
    ok: boolean
    signature?: string
    error?: string
    code?: string
    webFaucetUrl?: string
  }>
  sendSol: (to: string, sol: number) => Promise<{ signature: string; explorerBase: string }>
  sendSpl: (
    to: string,
    mint: string,
    uiAmount: number,
  ) => Promise<{ signature: string; explorerBase: string }>
  onLockChange: (callback: (unlocked: boolean) => void) => () => void
  session: WalletSessionApi
  panicSell: () => Promise<{
    ok: boolean
    drained?: boolean
    openCount?: number
    waitedMs?: number
    error?: string
  }>
}

export interface JarvisApi {
  minimizeWindow: () => void
  restoreWindow: () => void
  activateGuard: () => void
  deactivateGuard: () => void
  relockGuard: () => void
  showPinEntry: () => void
  onGuardCombo: (callback: () => void) => () => void
  onGuardAlarm: (callback: () => void) => () => void
  biometricAvailable: () => Promise<boolean>
  biometricVerify: (reason: string) => Promise<boolean>
  copyText: (text: string) => Promise<boolean>
  openExternal: (url: string) => Promise<boolean>
  wallet: WalletApi
  agents: AgentsApi
}

declare global {
  interface Window {
    electron: ElectronAPI
    api: JarvisApi
  }
}
