import { randomUUID } from 'crypto'
import { BrowserWindow } from 'electron'
import { LAMPORTS_PER_SOL } from '@solana/web3.js'
import { setAutoLockSuppressed } from './signer'

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
      setAutoLockSuppressed(false)
      notify()
    }
  }, input.durationSec * 1000)

  // While a session is active, suppress the wallet's inactivity auto-lock.
  // Otherwise the bot can be in the middle of selling positions when the
  // 30-minute timer fires and ends the session, leaving every subsequent
  // sell-tx rejected 403 by the loopback.
  setAutoLockSuppressed(true)

  notify()
  return active
}

export function endSession(): void {
  active = null
  clearExpiry()
  setAutoLockSuppressed(false)
  notify()
}

export function getActiveSession(): SessionPolicy | null {
  if (active && active.expiresAt < Date.now()) {
    active = null
    setAutoLockSuppressed(false)
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
  // Only enforce trade-size and budget caps on spend-side actions. Sells
  // bypass these checks because (a) they receive SOL rather than spend it
  // and (b) they need to drain even after the buy budget is exhausted.
  const isSpend = SPEND_ACTIONS.has(claim.action)
  if (isSpend) {
    const sol = claim.lamportsOut / LAMPORTS_PER_SOL
    if (sol > active.maxTradeSol) {
      return `trade size ${sol.toFixed(6)} SOL exceeds maxTradeSol ${active.maxTradeSol}`
    }
    if (active.spentSol + sol > active.totalBudgetSol + 1e-9) {
      return `would exceed totalBudgetSol (spent ${active.spentSol.toFixed(6)} + ${sol.toFixed(6)} > ${active.totalBudgetSol})`
    }
  }
  return null
}

// Actions that *spend* SOL — only these count against the budget cap.
// Sells receive SOL; counting them against the budget would (a) prematurely
// exhaust the budget and (b) end the session, leaving any held positions
// stuck on-chain because their sell signatures get 403'd.
const SPEND_ACTIONS = new Set<AutoAction>(['swap', 'transfer', 'pumpfun_buy'])

export function recordSpend(lamports: number, action?: AutoAction): void {
  if (!active) return
  // Only spend-side actions count toward the budget. Sells nominate a tiny
  // placeholder lamportsOut anyway (~10k for fee accounting), but we drop
  // them entirely so they don't drift the spentSol upward across many sells.
  if (action && !SPEND_ACTIONS.has(action)) return
  const sol = lamports / LAMPORTS_PER_SOL
  active.spentSol += sol
  notify()
  // Do NOT auto-end the session on budget exhaustion. The validateClaim()
  // gate above already rejects further BUY signs once the budget is hit
  // (which is how we want to stop opening new positions), but the session
  // must stay alive so the runner's sell-side path can keep signing exits.
  // Otherwise any held positions would be stranded.
}

export function onSessionChange(fn: (s: SessionPolicy | null) => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
