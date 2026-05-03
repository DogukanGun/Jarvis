import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'

type Network = 'mainnet' | 'devnet'
type CreateMode =
  | { kind: 'generate' }
  | { kind: 'mnemonic'; mnemonic: string }
  | { kind: 'base58'; base58: string }

type AutoStrategy = 'indicator' | 'copy_trade' | 'pumpfun_snipe'
type AutoAction = 'swap' | 'transfer' | 'pumpfun_buy' | 'pumpfun_sell'

interface SessionPolicyInput {
  strategy: AutoStrategy
  maxTradeSol: number
  totalBudgetSol: number
  durationSec: number
  allowedActions: AutoAction[]
  allowedMints?: string[]
}

interface SessionPolicy {
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

type SpawnState = 'not-installed' | 'spawning' | 'running' | 'crashed' | 'stopped'
interface AgentStatus {
  name: 'solana-trader' | 'solana-strategy' | 'legal-rag'
  state: SpawnState
  port: number
  pid: number | null
  logPath: string
  logTail: string[]
  lastError: string | null
}

type AgentSnapshot = { trader: AgentStatus; strategy: AgentStatus; legalRag: AgentStatus }

const agents = {
  status: (): Promise<AgentSnapshot> =>
    ipcRenderer.invoke('agents:status'),
  installTrader: (): Promise<{ ok: boolean; code: number | null }> =>
    ipcRenderer.invoke('agents:install-trader'),
  installStrategy: (): Promise<{ ok: boolean; code: number | null }> =>
    ipcRenderer.invoke('agents:install-strategy'),
  installLegalRag: (): Promise<{ ok: boolean; code: number | null }> =>
    ipcRenderer.invoke('agents:install-legal-rag'),
  restartTrader: (): Promise<AgentSnapshot> =>
    ipcRenderer.invoke('agents:restart-trader'),
  restartStrategy: (): Promise<AgentSnapshot> =>
    ipcRenderer.invoke('agents:restart-strategy'),
  restartLegalRag: (): Promise<AgentSnapshot> =>
    ipcRenderer.invoke('agents:restart-legal-rag'),
  startAll: (): Promise<AgentSnapshot> =>
    ipcRenderer.invoke('agents:start-all'),
  onStatusChange: (
    callback: (snapshot: AgentSnapshot) => void,
  ): (() => void) => {
    const handler = (_e: unknown, snapshot: AgentSnapshot): void => callback(snapshot)
    ipcRenderer.on('agents:status-changed', handler)
    return () => ipcRenderer.removeListener('agents:status-changed', handler)
  },
  onInstallLog: (callback: (line: string) => void): (() => void) => {
    const handler = (_e: unknown, line: string): void => callback(line)
    ipcRenderer.on('agents:install-log', handler)
    return () => ipcRenderer.removeListener('agents:install-log', handler)
  },
}

const wallet = {
  status: (): Promise<{
    hasVault: boolean
    isUnlocked: boolean
    publicKey: string | null
    config: { network: Network; rpcUrl: string; explorerBase: string; autoLockSeconds: number }
  }> => ipcRenderer.invoke('wallet:status'),
  create: (mode: CreateMode, pin: string): Promise<{ publicKey: string; mnemonic: string | null }> =>
    ipcRenderer.invoke('wallet:create', { mode, pin }),
  wipe: (): Promise<boolean> => ipcRenderer.invoke('wallet:wipe'),
  unlock: (pin: string): Promise<{ ok: boolean; publicKey?: string; error?: string }> =>
    ipcRenderer.invoke('wallet:unlock', pin),
  verifyPin: (pin: string): Promise<boolean> => ipcRenderer.invoke('wallet:verify-pin', pin),
  exportPrivateKey: (
    pin: string,
  ): Promise<{ ok: boolean; base58?: string; array?: number[]; error?: string }> =>
    ipcRenderer.invoke('wallet:export-private-key', pin),
  lock: (): Promise<boolean> => ipcRenderer.invoke('wallet:lock'),
  getConfig: (): Promise<{ network: Network; rpcUrl: string; explorerBase: string; autoLockSeconds: number }> =>
    ipcRenderer.invoke('wallet:get-config'),
  setConfig: (
    patch: Partial<{ network: Network; rpcUrl: string; explorerBase: string; autoLockSeconds: number }>,
  ): Promise<{ network: Network; rpcUrl: string; explorerBase: string; autoLockSeconds: number }> =>
    ipcRenderer.invoke('wallet:set-config', patch),
  getBalance: (): Promise<{
    publicKey: string
    sol: { lamports: number; sol: number }
    holdings: Array<{
      mint: string
      amount: string
      uiAmount: number
      decimals: number
      tokenAccount: string
      programId: string
    }>
    network: Network
  }> => ipcRenderer.invoke('wallet:get-balance'),
  airdrop: (
    sol: number,
  ): Promise<{ ok: boolean; signature?: string; error?: string; code?: string; webFaucetUrl?: string }> =>
    ipcRenderer.invoke('wallet:airdrop', sol),
  sendSol: (to: string, sol: number): Promise<{ signature: string; explorerBase: string }> =>
    ipcRenderer.invoke('wallet:send-sol', { to, sol }),
  sendSpl: (
    to: string,
    mint: string,
    uiAmount: number,
  ): Promise<{ signature: string; explorerBase: string }> =>
    ipcRenderer.invoke('wallet:send-spl', { to, mint, uiAmount }),
  onLockChange: (callback: (unlocked: boolean) => void): (() => void) => {
    const handler = (_e: unknown, unlocked: boolean): void => callback(unlocked)
    ipcRenderer.on('wallet:lock-changed', handler)
    return () => ipcRenderer.removeListener('wallet:lock-changed', handler)
  },
  session: {
    start: (input: SessionPolicyInput): Promise<SessionPolicy> =>
      ipcRenderer.invoke('wallet:session-start', input),
    status: (): Promise<SessionPolicy | null> => ipcRenderer.invoke('wallet:session-status'),
    end: (): Promise<boolean> => ipcRenderer.invoke('wallet:session-end'),
    onChange: (callback: (s: SessionPolicy | null) => void): (() => void) => {
      const handler = (_e: unknown, s: SessionPolicy | null): void => callback(s)
      ipcRenderer.on('wallet:session-changed', handler)
      return () => ipcRenderer.removeListener('wallet:session-changed', handler)
    },
  },
  panicSell: (): Promise<{ ok: boolean; drained?: boolean; openCount?: number; waitedMs?: number; error?: string }> =>
    ipcRenderer.invoke('wallet:panic-sell'),
}

const api = {
  minimizeWindow: (): void => ipcRenderer.send('minimize-window'),
  restoreWindow: (): void => ipcRenderer.send('restore-window'),
  activateGuard: (): void => ipcRenderer.send('guard-activate'),
  deactivateGuard: (): void => ipcRenderer.send('guard-deactivate'),
  relockGuard: (): void => ipcRenderer.send('guard-relock'),
  showPinEntry: (): void => ipcRenderer.send('guard-show-pin'),
  onGuardCombo: (callback: () => void): (() => void) => {
    const handler = (): void => callback()
    ipcRenderer.on('guard-combo-matched', handler)
    return () => ipcRenderer.removeListener('guard-combo-matched', handler)
  },
  onGuardAlarm: (callback: () => void): (() => void) => {
    const handler = (): void => callback()
    ipcRenderer.on('guard-alarm', handler)
    return () => ipcRenderer.removeListener('guard-alarm', handler)
  },
  biometricAvailable: (): Promise<boolean> => ipcRenderer.invoke('biometric-available'),
  biometricVerify: (reason: string): Promise<boolean> => ipcRenderer.invoke('biometric-verify', reason),
  copyText: (text: string): Promise<boolean> => ipcRenderer.invoke('clipboard:write-text', text),
  openExternal: (url: string): Promise<boolean> => ipcRenderer.invoke('shell:open-external', url),
  wallet,
  agents,
}

if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('electron', electronAPI)
    contextBridge.exposeInMainWorld('api', api)
  } catch (error) {
    console.error(error)
  }
} else {
  // @ts-ignore (define in dts)
  window.electron = electronAPI
  // @ts-ignore (define in dts)
  window.api = api
}
