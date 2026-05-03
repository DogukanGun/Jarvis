import { ipcMain, systemPreferences, BrowserWindow } from 'electron'
import {
  hasVault,
  getStoredPublicKey,
  createVault,
  wipeVault,
  unlockVault,
  exportSecretKey,
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
  installLegalRag,
  restartTrader,
  restartStrategy,
  restartLegalRag,
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

  ipcMain.handle('wallet:export-private-key', async (_e, pin: string) => {
    if (!pin) throw new Error('PIN required')
    // Two-factor: Touch ID first (proves the laptop owner is present),
    // then PIN-decrypt the vault (proves the PIN holder is present).
    const ok = await biometricGate('Reveal Solana private key')
    if (!ok) throw new Error('Biometric check failed')
    try {
      return { ok: true, ...exportSecretKey(pin) }
    } catch (err) {
      return { ok: false, error: (err as Error).message }
    }
  })

  ipcMain.handle('wallet:lock', () => {
    lock()
    return true
  })

  ipcMain.handle('wallet:get-config', () => loadConfig())

  ipcMain.handle('wallet:set-config', async (_e, patch: Partial<WalletConfig>) => {
    const before = loadConfig()
    const after = saveConfig(patch)
    // Network or RPC URL changes invalidate the env baked into the running
    // child processes. Respawn so they pick up the new RPC + NETWORK and the
    // Trade page stops showing devnet warnings on mainnet.
    const networkChanged = before.network !== after.network
    const rpcChanged = before.rpcUrl !== after.rpcUrl
    if ((networkChanged || rpcChanged) && isUnlocked()) {
      // Kill any active auto-trade session — the policy was authorized for
      // the previous network and shouldn't carry over.
      endSession()
      void restartTrader()
      void restartStrategy()
    }
    return after
  })

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
    try {
      const sig = await airdropDevnetSol(pub, sol)
      return { ok: true, signature: sig }
    } catch (e) {
      const err = e as Error & { code?: string; webFaucetUrl?: string }
      return {
        ok: false,
        error: err.message,
        code: err.code,
        webFaucetUrl: err.webFaucetUrl,
      }
    }
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

  ipcMain.handle('agents:install-legal-rag', async (event) => {
    const sender = event.sender
    const result = await installLegalRag((line) => {
      if (!sender.isDestroyed()) sender.send('agents:install-log', line)
    })
    return result
  })

  ipcMain.handle('agents:restart-legal-rag', async () => {
    await restartLegalRag()
    return getStatusSnapshot()
  })

  ipcMain.handle('agents:start-all', async () => {
    if (!isUnlocked()) throw new Error('Wallet is locked')
    await startAll()
    return getStatusSnapshot()
  })

  // ── Auto-trade session policy ────────────────────────────────────────────
  // NOTE: we deliberately do NOT end the session on wallet lock. Auto-lock
  // is suppressed while a session is active (see signer.setAutoLockSuppressed),
  // and a manual lock by the user is rare enough that we'd rather leave the
  // policy intact and let the loopback's 423 response surface to the UI than
  // silently nuke an in-flight session.

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

  // Panic-sell — fire-and-wait. Posts to the strategy's /api/auto/panic and
  // waits up to 30s for the runner to drain. Used by the 🚨 UI button and
  // by the Electron `before-quit` hook so quitting the app doesn't leave
  // bought tokens stuck on-chain.
  ipcMain.handle('wallet:panic-sell', async () => {
    const STRATEGY = 'http://127.0.0.1:8902'
    const DEADLINE_MS = 30_000
    let drained = false
    let openCount = -1
    try {
      await fetch(`${STRATEGY}/api/auto/panic`, { method: 'POST' })
    } catch (e) {
      return { ok: false, error: `panic POST failed: ${(e as Error).message}` }
    }
    const start = Date.now()
    while (Date.now() - start < DEADLINE_MS) {
      try {
        const r = await fetch(`${STRATEGY}/api/auto/status`)
        if (r.ok) {
          const j = (await r.json()) as { open_positions?: unknown[]; running?: boolean }
          openCount = (j.open_positions ?? []).length
          if (openCount === 0 || !j.running) {
            drained = true
            break
          }
        }
      } catch { /* keep polling */ }
      await new Promise((res) => setTimeout(res, 1000))
    }
    return { ok: true, drained, openCount, waitedMs: Date.now() - start }
  })
}
