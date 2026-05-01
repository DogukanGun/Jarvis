import { randomUUID } from 'crypto'
import { BrowserWindow } from 'electron'
import { LAMPORTS_PER_SOL } from '@solana/web3.js'

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

export interface SignClaim {
  action: AutoAction
  lamportsOut: number
  mint?: string
}

let active: SessionPolicy | null = null
let expiryTimer: NodeJS.Timeout | null = null

const listeners = new Set<(s: SessionPolicy | null) => void>()

function notify(): void {
  for (const fn of listeners) {
    try { fn(active) } catch { /* ignore */ }
  }
  for (const win of BrowserWindow.getAllWindows()) {
    win.webContents.send('wallet:session-changed', active)
  }
}

function clearExpiry(): void {
  if (expiryTimer) {
    clearTimeout(expiryTimer)
    expiryTimer = null
  }
}

export function startSession(input: SessionPolicyInput): SessionPolicy {
  if (active) throw new Error('A session is already active. End it first.')
  if (input.maxTradeSol <= 0) throw new Error('maxTradeSol must be > 0')
  if (input.totalBudgetSol <= 0) throw new Error('totalBudgetSol must be > 0')
  if (input.totalBudgetSol < input.maxTradeSol) {
    throw new Error('totalBudgetSol must be >= maxTradeSol')
  }
  if (input.durationSec < 60 || input.durationSec > 86_400) {
    throw new Error('durationSec must be between 60 and 86400')
  }
  if (input.allowedActions.length === 0) throw new Error('allowedActions cannot be empty')

  const now = Date.now()
  active = {
    id: randomUUID(),
    strategy: input.strategy,
    maxTradeSol: input.maxTradeSol,
    totalBudgetSol: input.totalBudgetSol,
    spentSol: 0,
    expiresAt: now + input.durationSec * 1000,
    startedAt: now,
    allowedActions: [...input.allowedActions],
    allowedMints: input.allowedMints ? [...input.allowedMints] : undefined,
  }

  clearExpiry()
  expiryTimer = setTimeout(() => {
    if (active) {
      active = null
      notify()
    }
  }, input.durationSec * 1000)

  notify()
  return active
}

export function endSession(): void {
  active = null
  clearExpiry()
  notify()
}

export function getActiveSession(): SessionPolicy | null {
  if (active && active.expiresAt < Date.now()) {
    active = null
    notify()
  }
  return active
}

// Verify a signing claim against the active policy. Returns null on success
// (allowed), or a string describing the rejection reason.
export function validateClaim(policyId: string, claim: SignClaim): string | null {
  if (!active) return 'no active session'
  if (active.id !== policyId) return 'policy id mismatch'
  if (Date.now() > active.expiresAt) {
    active = null
    notify()
    return 'session expired'
  }
  if (!active.allowedActions.includes(claim.action)) {
    return `action ${claim.action} not in allow-list`
  }
  if (active.allowedMints && claim.mint && !active.allowedMints.includes(claim.mint)) {
    return `mint ${claim.mint} not in allow-list`
  }
  const sol = claim.lamportsOut / LAMPORTS_PER_SOL
  if (sol > active.maxTradeSol) {
    return `trade size ${sol.toFixed(6)} SOL exceeds maxTradeSol ${active.maxTradeSol}`
  }
  if (active.spentSol + sol > active.totalBudgetSol + 1e-9) {
    return `would exceed totalBudgetSol (spent ${active.spentSol.toFixed(6)} + ${sol.toFixed(6)} > ${active.totalBudgetSol})`
  }
  return null
}

export function recordSpend(lamports: number): void {
  if (!active) return
  const sol = lamports / LAMPORTS_PER_SOL
  active.spentSol += sol
  notify()
  // Auto-end on budget exhaustion.
  if (active.spentSol + 1e-9 >= active.totalBudgetSol) {
    active = null
    clearExpiry()
    notify()
  }
}

export function onSessionChange(fn: (s: SessionPolicy | null) => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
