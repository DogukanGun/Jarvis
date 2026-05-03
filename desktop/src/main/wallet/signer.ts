import { Keypair, Transaction, VersionedTransaction } from '@solana/web3.js'
import { unlockVault } from './vault'
import { loadConfig } from './config'

let kp: Keypair | null = null
let lockTimer: NodeJS.Timeout | null = null
let autoLockSuppressed = false
const listeners = new Set<(unlocked: boolean) => void>()

function notify(unlocked: boolean): void {
  for (const fn of listeners) {
    try { fn(unlocked) } catch { /* ignore */ }
  }
}

function resetAutoLock(): void {
  if (lockTimer) clearTimeout(lockTimer)
  if (autoLockSuppressed) return
  const seconds = loadConfig().autoLockSeconds
  if (seconds <= 0) return
  lockTimer = setTimeout(() => lock(), seconds * 1000)
}

/** Pause/resume the inactivity-based auto-lock timer. Used by the auto-trade
 *  session so the wallet doesn't lock mid-snipe-loop just because no manual
 *  signing has happened in the last 30 minutes. Manual lock (user clicks
 *  Lock, or app quits) still fires through `lock()`. */
export function setAutoLockSuppressed(suppressed: boolean): void {
  autoLockSuppressed = suppressed
  if (suppressed) {
    if (lockTimer) {
      clearTimeout(lockTimer)
      lockTimer = null
    }
  } else {
    resetAutoLock()
  }
}

export function isUnlocked(): boolean {
  return kp !== null
}

export function getPublicKey(): string | null {
  return kp?.publicKey.toBase58() ?? null
}

export function unlockSigner(pin: string): string {
  kp = unlockVault(pin)
  resetAutoLock()
  notify(true)
  return kp.publicKey.toBase58()
}

export function lock(): void {
  if (kp) {
    // Best-effort wipe — secretKey is a Uint8Array reference.
    try { kp.secretKey.fill(0) } catch { /* ignore */ }
  }
  kp = null
  if (lockTimer) {
    clearTimeout(lockTimer)
    lockTimer = null
  }
  notify(false)
}

export function getKeypairForRequest(): Keypair {
  if (!kp) throw new Error('Wallet is locked')
  resetAutoLock()
  return kp
}

export function signTransaction<T extends Transaction | VersionedTransaction>(tx: T): T {
  const k = getKeypairForRequest()
  if (tx instanceof VersionedTransaction) {
    tx.sign([k])
  } else {
    tx.partialSign(k)
  }
  return tx
}

export function onLockChange(fn: (unlocked: boolean) => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
