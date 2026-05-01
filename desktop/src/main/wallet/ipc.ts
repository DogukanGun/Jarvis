import { ipcMain, systemPreferences, BrowserWindow } from 'electron'
import {
  hasVault,
  getStoredPublicKey,
  createVault,
  wipeVault,
  unlockVault,
  type CreateMode,
} from './vault'
import {
  isUnlocked,
  unlockSigner,
  lock,
  getKeypairForRequest,
  getPublicKey as getSignerPubkey,
  onLockChange,
} from './signer'
import { loadConfig, saveConfig, type WalletConfig } from './config'
import {
  getSolBalance,
  getTokenHoldings,
  sendSol,
  sendSpl,
  airdropDevnetSol,
} from './rpc'
import { bindLoopbackToSigner, getLoopbackInfo, isLoopbackRunning } from './loopback'
import {
  bindAgentSpawnerToSigner,
  getStatusSnapshot,
  installTrader,
  installStrategy,
  restartTrader,
  restartStrategy,
  startAll,
} from './agent-spawner'
import {
  startSession,
  endSession,
  getActiveSession,
  type SessionPolicyInput,
} from './session'

async function biometricGate(reason: string): Promise<boolean> {
  if (process.platform !== 'darwin') return true
  if (!systemPreferences.canPromptTouchID()) return true
  try {
    await systemPreferences.promptTouchID(reason)
    return true
  } catch {
    return false
  }
}

function broadcastLock(unlocked: boolean): void {
  for (const win of BrowserWindow.getAllWindows()) {
    win.webContents.send('wallet:lock-changed', unlocked)
  }
}

export function registerWalletIpc(): void {
  onLockChange(broadcastLock)
  bindLoopbackToSigner()
  bindAgentSpawnerToSigner()

  ipcMain.handle('wallet:loopback-info', () => {
    if (!isLoopbackRunning()) return null
    return getLoopbackInfo()
  })

  ipcMain.handle('wallet:status', () => ({
    hasVault: hasVault(),
    isUnlocked: isUnlocked(),
    publicKey: getSignerPubkey() ?? getStoredPublicKey(),
    config: loadConfig(),
  }))

  ipcMain.handle('wallet:create', async (_e, payload: { mode: CreateMode; pin: string }) => {
    if (!payload?.mode || !payload?.pin) throw new Error('Missing mode or PIN')
    const result = createVault(payload.mode, payload.pin)
    // Auto-unlock right after create — user just typed the PIN.
    unlockSigner(payload.pin)
    return result
  })

  ipcMain.handle('wallet:wipe', async () => {
    const ok = await biometricGate('Confirm wallet deletion')
    if (!ok) throw new Error('Biometric check failed')
    lock()
    wipeVault()
    return true
  })

  ipcMain.handle('wallet:unlock', async (_e, pin: string) => {
    if (!pin) throw new Error('PIN required')
    try {
      const publicKey = unlockSigner(pin)
      return { ok: true, publicKey }
    } catch (err) {
      return { ok: false, error: (err as Error).message }
    }
  })

  ipcMain.handle('wallet:verify-pin', (_e, pin: string) => {
    try {
      // Decrypt without persisting in signer.
      unlockVault(pin)
      return true
    } catch {
      return false
    }
  })

  ipcMain.handle('wallet:lock', () => {
    lock()
    return true
  })

  ipcMain.handle('wallet:get-config', () => loadConfig())

  ipcMain.handle('wallet:set-config', (_e, patch: Partial<WalletConfig>) => saveConfig(patch))

  ipcMain.handle('wallet:get-balance', async () => {
    const pub = getSignerPubkey() ?? getStoredPublicKey()
    if (!pub) throw new Error('No wallet')
    const [sol, holdings] = await Promise.all([
      getSolBalance(pub),
      getTokenHoldings(pub).catch(() => []),
    ])
    return { publicKey: pub, sol, holdings, network: loadConfig().network }
  })

  ipcMain.handle('wallet:airdrop', async (_e, sol: number) => {
    const pub = getSignerPubkey() ?? getStoredPublicKey()
    if (!pub) throw new Error('No wallet')
    return airdropDevnetSol(pub, sol)
  })

  ipcMain.handle(
    'wallet:send-sol',
    async (_e, payload: { to: string; sol: number }) => {
      if (!isUnlocked()) throw new Error('Wallet is locked')
      const ok = await biometricGate(`Send ${payload.sol} SOL to ${payload.to.slice(0, 8)}…`)
      if (!ok) throw new Error('Biometric check failed')
      const kp = getKeypairForRequest()
      const sig = await sendSol(kp, payload.to, payload.sol)
      return { signature: sig, explorerBase: loadConfig().explorerBase }
    },
  )

  ipcMain.handle(
    'wallet:send-spl',
    async (_e, payload: { to: string; mint: string; uiAmount: number }) => {
      if (!isUnlocked()) throw new Error('Wallet is locked')
      const ok = await biometricGate(`Send ${payload.uiAmount} of token ${payload.mint.slice(0, 6)}…`)
      if (!ok) throw new Error('Biometric check failed')
      const kp = getKeypairForRequest()
      const sig = await sendSpl(kp, payload.to, payload.mint, payload.uiAmount)
      return { signature: sig, explorerBase: loadConfig().explorerBase }
    },
  )

  // ── Agent spawner status / install / restart ──────────────────────────────
  ipcMain.handle('agents:status', () => getStatusSnapshot())

  ipcMain.handle('agents:install-trader', async (event) => {
    const sender = event.sender
    const result = await installTrader((line) => {
      if (!sender.isDestroyed()) sender.send('agents:install-log', line)
    })
    return result
  })

  ipcMain.handle('agents:install-strategy', async (event) => {
    const sender = event.sender
    const result = await installStrategy((line) => {
      if (!sender.isDestroyed()) sender.send('agents:install-log', line)
    })
    return result
  })

  ipcMain.handle('agents:restart-trader', async () => {
    await restartTrader()
    return getStatusSnapshot()
  })

  ipcMain.handle('agents:restart-strategy', async () => {
    await restartStrategy()
    return getStatusSnapshot()
  })

  ipcMain.handle('agents:start-all', async () => {
    if (!isUnlocked()) throw new Error('Wallet is locked')
    await startAll()
    return getStatusSnapshot()
  })

  // ── Auto-trade session policy ────────────────────────────────────────────
  // Lock-on-wallet-lock: ending the wallet lock kills the session.
  onLockChange((unlocked) => {
    if (!unlocked) endSession()
  })

  ipcMain.handle('wallet:session-start', async (_e, input: SessionPolicyInput) => {
    if (!isUnlocked()) throw new Error('Wallet is locked')
    const summary =
      `Authorize ${input.strategy} auto-trade · max ${input.maxTradeSol} SOL/trade · budget ${input.totalBudgetSol} SOL · ${Math.round(input.durationSec / 60)}m`
    const ok = await biometricGate(summary)
    if (!ok) throw new Error('Biometric check failed')
    const session = startSession(input)
    return session
  })

  ipcMain.handle('wallet:session-status', () => getActiveSession())

  ipcMain.handle('wallet:session-end', () => {
    endSession()
    return true
  })
}
