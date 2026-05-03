import { useCallback, useEffect, useRef, useState } from 'react'

const TRADER_BASE = 'http://localhost:8901'
const STRATEGY_BASE = 'http://localhost:8902'

type Tab = 'swap' | 'pumpfun' | 'strategy' | 'auto'

type SpawnState = 'not-installed' | 'spawning' | 'running' | 'crashed' | 'stopped'

interface AgentStatus {
  name: 'solana-trader' | 'solana-strategy'
  state: SpawnState
  port: number
  pid: number | null
  logPath: string
  logTail: string[]
  lastError: string | null
}

interface Props {
  onBack: () => void
}

interface TraderHealth {
  ok: boolean
  publicKey?: string
  network?: string
  error?: string
}

interface Intent {
  action: string
  params: Record<string, unknown>
  reason: string
  confidence: number
}

interface StrategyResponse {
  response: string
  tools_used: string[]
  intents: Intent[]
  findings: Array<{ tool: string; details?: { raw_output?: string } }>
}

const SHORT = (s: string, n = 6): string => `${s.slice(0, n)}…${s.slice(-4)}`

export default function Trade({ onBack }: Props): React.JSX.Element {
  const [tab, setTab] = useState<Tab>('swap')
  const [health, setHealth] = useState<TraderHealth>({ ok: false })
  const [traderStatus, setTraderStatus] = useState<AgentStatus | null>(null)
  const [strategyStatus, setStrategyStatus] = useState<AgentStatus | null>(null)
  const [installing, setInstalling] = useState(false)
  const [installLog, setInstallLog] = useState<string[]>([])

  // Swap state
  const [inputMint, setInputMint] = useState('So11111111111111111111111111111111111111112') // wSOL
  const [outputMint, setOutputMint] = useState('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v') // USDC mainnet
  const [amount, setAmount] = useState('0.01')
  const [slippageBps, setSlippageBps] = useState('100')
  const [swapBusy, setSwapBusy] = useState(false)
  const [swapResult, setSwapResult] = useState<{ signature: string } | null>(null)

  // Pump.fun state
  const [pfName, setPfName] = useState('')
  const [pfTicker, setPfTicker] = useState('')
  const [pfDescription, setPfDescription] = useState('')
  const [pfImageUrl, setPfImageUrl] = useState('')
  const [pfBusy, setPfBusy] = useState(false)
  const [pfResult, setPfResult] = useState<unknown>(null)

  // Strategy state
  const [strategyPrompt, setStrategyPrompt] = useState(
    'Should I buy SOL right now? Run indicator analysis on the SOL/USDC 15m chart.',
  )
  const [strategyBusy, setStrategyBusy] = useState(false)
  const [strategyResp, setStrategyResp] = useState<StrategyResponse | null>(null)
  const [executing, setExecuting] = useState(false)

  const [error, setError] = useState<string | null>(null)
  const lastError = useRef<string | null>(null)

  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(`${TRADER_BASE}/health`)
      if (!res.ok) throw new Error(`trader returned ${res.status}`)
      const j = (await res.json()) as { ok: boolean; publicKey?: string; network?: string }
      setHealth({ ok: true, publicKey: j.publicKey, network: j.network })
    } catch (e) {
      setHealth({ ok: false, error: (e as Error).message })
    }
  }, [])

  const onDevnet = health.network === 'devnet'

  useEffect(() => {
    void checkHealth()
    const id = setInterval(checkHealth, 5000)
    return () => clearInterval(id)
  }, [checkHealth])

  useEffect(() => {
    void window.api.agents.status().then((s) => {
      setTraderStatus(s.trader)
      setStrategyStatus(s.strategy)
    })
    const offStatus = window.api.agents.onStatusChange((s) => {
      setTraderStatus(s.trader)
      setStrategyStatus(s.strategy)
    })
    const offLog = window.api.agents.onInstallLog((line) => {
      setInstallLog((prev) => [...prev.slice(-200), line])
    })
    return () => {
      offStatus()
      offLog()
    }
  }, [])

  async function handleInstallTrader(): Promise<void> {
    setInstalling(true)
    setInstallLog([])
    try {
      const result = await window.api.agents.installTrader()
      if (!result.ok) {
        setInstallLog((prev) => [...prev, `[install] failed (exit ${result.code})`])
      }
    } finally {
      setInstalling(false)
    }
  }

  async function handleInstallStrategy(): Promise<void> {
    setInstalling(true)
    setInstallLog([])
    try {
      const result = await window.api.agents.installStrategy()
      if (!result.ok) {
        setInstallLog((prev) => [...prev, `[install] failed (exit ${result.code})`])
      }
    } finally {
      setInstalling(false)
    }
  }

  async function handleRestartTrader(): Promise<void> {
    await window.api.agents.restartTrader()
  }

  async function handleRestartStrategy(): Promise<void> {
    await window.api.agents.restartStrategy()
  }

  function fail(msg: string): void {
    lastError.current = msg
    setError(msg)
  }

  async function postJson<T>(url: string, body: unknown): Promise<T> {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const txt = await res.text()
      throw new Error(`${res.status}: ${txt}`)
    }
    return (await res.json()) as T
  }

  async function handleSwap(): Promise<void> {
    setError(null)
    if (onDevnet) {
      return fail('Jupiter swap requires mainnet. Switch network on the Wallet page.')
    }
    const amt = parseFloat(amount)
    if (!Number.isFinite(amt) || amt <= 0) return fail('Invalid amount')
    setSwapBusy(true)
    try {
      const out = await postJson<{ signature: string }>(`${TRADER_BASE}/api/swap`, {
        outputMint,
        amount: amt,
        inputMint: inputMint || undefined,
        slippageBps: Number(slippageBps) || 100,
      })
      setSwapResult(out)
    } catch (e) {
      fail((e as Error).message)
    } finally {
      setSwapBusy(false)
    }
  }

  async function handleLaunchPumpfun(): Promise<void> {
    setError(null)
    if (onDevnet) {
      return fail('Pump.fun is mainnet-only. Switch network on the Wallet page.')
    }
    if (!pfName || !pfTicker || !pfDescription || !pfImageUrl) {
      return fail('Fill in name, ticker, description, image URL')
    }
    setPfBusy(true)
    try {
      const out = await postJson(`${TRADER_BASE}/api/pumpfun/launch`, {
        tokenName: pfName,
        tokenTicker: pfTicker,
        description: pfDescription,
        imageUrl: pfImageUrl,
      })
      setPfResult(out)
    } catch (e) {
      fail((e as Error).message)
    } finally {
      setPfBusy(false)
    }
  }

  async function runStrategy(): Promise<void> {
    setError(null)
    setStrategyResp(null)
    setStrategyBusy(true)
    try {
      const out = await postJson<StrategyResponse>(`${STRATEGY_BASE}/api/execute`, {
        message: strategyPrompt,
        confirmed: false,
      })
      setStrategyResp(out)
    } catch (e) {
      fail((e as Error).message)
    } finally {
      setStrategyBusy(false)
    }
  }

  async function executeIntent(intent: Intent): Promise<void> {
    setError(null)
    setExecuting(true)
    try {
      const out = await postJson<{ signature: string }>(`${TRADER_BASE}/api/execute-intent`, {
        action: intent.action,
        params: intent.params,
        sourceAgent: 'desktop-trade',
      })
      setSwapResult(out)
    } catch (e) {
      fail((e as Error).message)
    } finally {
      setExecuting(false)
    }
  }

  return (
    <div className="trade-page">
      <div className="trade-topbar">
        <button className="wallet-btn-secondary wallet-btn-sm" onClick={onBack}>
          ← Wallet
        </button>
        <div className="trade-tabs">
          <button className={`trade-tab ${tab === 'swap' ? 'active' : ''}`} onClick={() => setTab('swap')}>
            Swap
          </button>
          <button className={`trade-tab ${tab === 'pumpfun' ? 'active' : ''}`} onClick={() => setTab('pumpfun')}>
            Pump.fun
          </button>
          <button
            className={`trade-tab ${tab === 'strategy' ? 'active' : ''}`}
            onClick={() => setTab('strategy')}
          >
            Strategy
          </button>
          <button
            className={`trade-tab ${tab === 'auto' ? 'active' : ''}`}
            onClick={() => setTab('auto')}
          >
            Auto-Trade
          </button>
        </div>
        <div className={`trade-health ${health.ok ? 'ok' : 'bad'}`}>
          {health.ok
            ? `trader · ${health.network} · ${health.publicKey ? SHORT(health.publicKey, 6) : ''}`
            : `trader ${traderStatus?.state ?? 'offline'}`}
        </div>
      </div>

      <SpawnPanel
        title="TRADER SERVICE"
        status={traderStatus}
        installing={installing}
        installLog={installLog}
        installLabel="Install dependencies"
        notInstalledHint="The Solana trader process needs its dependencies installed before it can start. This is a one-time step."
        onInstall={handleInstallTrader}
        onRestart={handleRestartTrader}
      />

      <SpawnPanel
        title="STRATEGY SERVICE"
        status={strategyStatus}
        installing={installing}
        installLog={installLog}
        installLabel="Reinstall Python deps"
        notInstalledHint="Run ./run_local.sh once to bootstrap the venv, or reinstall here."
        onInstall={handleInstallStrategy}
        onRestart={handleRestartStrategy}
      />

      {onDevnet && (
        <div className="trade-devnet-banner">
          <strong>You're on devnet.</strong> Jupiter swap, Pump.fun, and the
          indicator/copy-trade auto strategies all require <em>mainnet</em>.
          Devnet has no DEX liquidity — only SOL/SPL transfers will work here.
          Switch network in the Wallet page to use trading features.
        </div>
      )}


      {error && <div className="wallet-error">{error}</div>}

      {tab === 'swap' && (
        <div className="trade-panel">
          <div className="trade-panel-title">JUPITER SWAP</div>
          <label className="trade-label">From mint (input)</label>
          <input className="wallet-input" value={inputMint} onChange={(e) => setInputMint(e.target.value)} />
          <label className="trade-label">To mint (output)</label>
          <input className="wallet-input" value={outputMint} onChange={(e) => setOutputMint(e.target.value)} />
          <div className="trade-row">
            <div className="trade-col">
              <label className="trade-label">Amount</label>
              <input className="wallet-input" value={amount} onChange={(e) => setAmount(e.target.value)} />
            </div>
            <div className="trade-col">
              <label className="trade-label">Slippage (bps)</label>
              <input
                className="wallet-input"
                value={slippageBps}
                onChange={(e) => setSlippageBps(e.target.value)}
              />
            </div>
          </div>
          <div className="wallet-actions">
            <button
              className="wallet-btn-primary"
              disabled={swapBusy || !health.ok}
              onClick={handleSwap}
            >
              {swapBusy ? 'Swapping…' : 'Swap'}
            </button>
          </div>
          {swapResult && <SignatureToast signature={swapResult.signature} network={health.network} />}
        </div>
      )}

      {tab === 'pumpfun' && (
        <div className="trade-panel">
          <div className="trade-panel-title">PUMP.FUN LAUNCH</div>
          <p className="wallet-subtitle" style={{ textAlign: 'left' }}>
            Launch a new memecoin on Pump.fun&apos;s bonding curve. Mainnet only.
          </p>
          <label className="trade-label">Name</label>
          <input className="wallet-input" value={pfName} onChange={(e) => setPfName(e.target.value)} />
          <label className="trade-label">Ticker</label>
          <input className="wallet-input" value={pfTicker} onChange={(e) => setPfTicker(e.target.value)} />
          <label className="trade-label">Description</label>
          <input
            className="wallet-input"
            value={pfDescription}
            onChange={(e) => setPfDescription(e.target.value)}
          />
          <label className="trade-label">Image URL</label>
          <input
            className="wallet-input"
            value={pfImageUrl}
            onChange={(e) => setPfImageUrl(e.target.value)}
          />
          <div className="wallet-actions">
            <button
              className="wallet-btn-primary"
              disabled={pfBusy || !health.ok}
              onClick={handleLaunchPumpfun}
            >
              {pfBusy ? 'Launching…' : 'Launch token'}
            </button>
          </div>
          {pfResult ? (
            <pre className="trade-pre">{JSON.stringify(pfResult, null, 2)}</pre>
          ) : null}
        </div>
      )}

      {tab === 'strategy' && (
        <div className="trade-panel">
          <div className="trade-panel-title">INDICATOR STRATEGY</div>
          <p className="wallet-subtitle" style={{ textAlign: 'left' }}>
            The strategy agent fetches OHLCV, computes EMA/RSI/Bollinger, and emits a TradeIntent.
            It never signs — confirm an intent here to forward to the trader.
          </p>
          <textarea
            className="wallet-textarea"
            rows={3}
            value={strategyPrompt}
            onChange={(e) => setStrategyPrompt(e.target.value)}
          />
          <div className="wallet-actions">
            <button
              className="wallet-btn-primary"
              disabled={strategyBusy}
              onClick={runStrategy}
            >
              {strategyBusy ? 'Analysing…' : 'Run strategy'}
            </button>
          </div>

          {strategyResp && (
            <div className="trade-strategy-result">
              <div className="trade-result-section">
                <div className="trade-result-label">REASONING</div>
                <div className="trade-result-text">{strategyResp.response || '(no answer)'}</div>
              </div>

              {strategyResp.intents.length > 0 ? (
                <div className="trade-result-section">
                  <div className="trade-result-label">EMITTED INTENTS</div>
                  {strategyResp.intents.map((intent, i) => (
                    <div className="trade-intent-card" key={i}>
                      <div className="trade-intent-head">
                        <span className="trade-intent-action">{intent.action}</span>
                        <span className="trade-intent-conf">conf {intent.confidence.toFixed(2)}</span>
                      </div>
                      <div className="trade-intent-reason">{intent.reason}</div>
                      <pre className="trade-pre">{JSON.stringify(intent.params, null, 2)}</pre>
                      <div className="wallet-actions">
                        <button
                          className="wallet-btn-primary"
                          disabled={executing || !health.ok}
                          onClick={() => void executeIntent(intent)}
                        >
                          {executing ? 'Executing…' : 'Confirm with Touch ID & execute'}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="trade-result-section">
                  <div className="trade-result-label">NO INTENT</div>
                  <div className="trade-result-text">
                    Strategy decided to hold. No execution requested.
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {tab === 'auto' && <AutoTradeTab traderRunning={!!health.ok} onDevnet={onDevnet} />}
    </div>
  )
}

// ── Auto-Trade tab ────────────────────────────────────────────────────────────

type AutoStrategyKey = 'indicator' | 'copy_trade' | 'pumpfun_snipe'

interface AutoEvent {
  ts: number
  kind: string
  [key: string]: unknown
}

interface OpenPosition {
  mint: string
  symbol?: string
  entry_price: number
  entry_sol: number
  quantity: number
  age_sec: number
  take_profit_price: number | null
  stop_loss_price: number | null
  max_hold_time: number | null
  sell_attempted: boolean
  last_error: string | null
}

interface SessionPolicy {
  id: string
  strategy: AutoStrategyKey
  maxTradeSol: number
  totalBudgetSol: number
  spentSol: number
  expiresAt: number
  startedAt: number
  allowedActions: string[]
}

function AutoTradeTab({
  traderRunning,
  onDevnet,
}: {
  traderRunning: boolean
  onDevnet: boolean
}): React.JSX.Element {
  const [strategy, setStrategy] = useState<AutoStrategyKey>('indicator')
  const [maxTradeSol, setMaxTradeSol] = useState('0.01')
  const [totalBudgetSol, setTotalBudgetSol] = useState('0.05')
  const [intervalSec, setIntervalSec] = useState('30')
  // Exit strategy (chainstacklabs Position semantics).
  // Max-hold defaults to EMPTY = "hold until I stop it (or TP/SL fires)".
  // The runner exits naturally only when (a) you click Stop & drain, (b) the
  // 🚨 button is pressed, or (c) a TP/SL condition fires. This matches the
  // user's expectation of "work until I stop it".
  const [takeProfitPct, setTakeProfitPct] = useState('50')   // %
  const [stopLossPct, setStopLossPct] = useState('30')       // %
  const [maxHoldSec, setMaxHoldSec] = useState('')           // seconds; empty = hold forever

  // Indicator config
  const [watchlist, setWatchlist] = useState('So11111111111111111111111111111111111111112')
  // Copy-trade config
  const [targetWallets, setTargetWallets] = useState('')
  const [copyRatio, setCopyRatio] = useState('0.01')
  // Pump-snipe config
  const [rugScoreMax, setRugScoreMax] = useState('0.5')
  const [minLiquiditySol, setMinLiquiditySol] = useState('5')
  const [maxBuySol, setMaxBuySol] = useState('0.005')

  const [session, setSession] = useState<SessionPolicy | null>(null)
  const [events, setEvents] = useState<AutoEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [sessionLost, setSessionLost] = useState<{ stuck: string[] } | null>(null)
  const [panic, setPanic] = useState<{ active: boolean; reason: string | null }>({ active: false, reason: null })
  const [openCount, setOpenCount] = useState(0)
  const [positions, setPositions] = useState<OpenPosition[]>([])
  const esRef = useRef<EventSource | null>(null)

  // Subscribe to session changes from main.
  useEffect(() => {
    void window.api.wallet.session.status().then(setSession)
    const off = window.api.wallet.session.onChange(setSession)
    return () => off()
  }, [])

  // SSE subscription to strategy events. Stays open across the whole
  // Auto-Trade tab session — even if the policy gets nuked we still want
  // to show what's happening (so the user can see "session-lost" events
  // and know they need to re-authorize).
  useEffect(() => {
    if (esRef.current) return
    const es = new EventSource('http://localhost:8902/api/auto/events')
    esRef.current = es
    es.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data) as AutoEvent
        setEvents((prev) => [...prev.slice(-300), ev])
        if (ev.kind === 'session-lost') {
          const stuck = (ev.stuck_positions as string[]) ?? []
          setSessionLost({ stuck })
        }
        if (ev.kind === 'panic-mode-entered') {
          setPanic({ active: true, reason: (ev.reason as string) || 'unknown' })
        }
        if (ev.kind === 'stopped' || ev.kind === 'drained' || ev.kind === 'ended') {
          setPanic({ active: false, reason: null })
        }
      } catch { /* ignore */ }
    }
    es.onerror = () => { /* strategy down or stream paused — leave silently */ }
    return () => {
      es.close()
      esRef.current = null
    }
  }, [])

  // Dead-man's-switch: while the Auto-Trade tab is mounted, send a
  // heartbeat to the strategy every 5 s. The watchdog there enters
  // panic-sell if it doesn't see a heartbeat for 60 s — i.e. closing
  // the tab, navigating away, or shutting the app triggers liquidation.
  useEffect(() => {
    let cancelled = false
    const ping = (): void => {
      void fetch('http://localhost:8902/api/auto/heartbeat', { method: 'POST' })
        .catch(() => { /* strategy down — watchdog there is the safety net */ })
    }
    ping()
    const id = setInterval(() => { if (!cancelled) ping() }, 5000)
    return () => { cancelled = true; clearInterval(id) }
  }, [])

  // Poll status to keep open-positions, panic indicator, and the visual
  // positions panel fresh. SSE covers most updates but the position list
  // is part of the status response, not the event stream.
  useEffect(() => {
    let cancelled = false
    const refresh = async (): Promise<void> => {
      try {
        const r = await fetch('http://localhost:8902/api/auto/status')
        if (!r.ok) return
        const j = (await r.json()) as {
          open_positions?: OpenPosition[]
          panic?: boolean
          panic_reason?: string | null
        }
        if (cancelled) return
        const list = j.open_positions ?? []
        setPositions(list)
        setOpenCount(list.length)
        if (j.panic) setPanic({ active: true, reason: j.panic_reason ?? null })
      } catch { /* */ }
    }
    void refresh()
    // 3s poll while the tab is mounted — covers fresh price-target proximity
    // and age countdown for the visual cards.
    const id = setInterval(refresh, 3000)
    return () => { cancelled = true; clearInterval(id) }
  }, [])

  const allowedActions = (): string[] => {
    if (strategy === 'indicator' || strategy === 'copy_trade') return ['swap']
    return ['pumpfun_buy', 'pumpfun_sell']
  }

  async function handleStart(): Promise<void> {
    setError(null)
    if (onDevnet) {
      return setError(
        'Auto-trade requires mainnet. All three strategies (indicator / copy-trade / pumpfun_snipe) need DEX liquidity that devnet does not have. Switch network on the Wallet page.',
      )
    }
    const max = parseFloat(maxTradeSol)
    const total = parseFloat(totalBudgetSol)
    const interval = parseInt(intervalSec, 10)
    const tpPct = parseFloat(takeProfitPct)
    const slPct = parseFloat(stopLossPct)
    const maxHold = parseInt(maxHoldSec, 10)
    if (!Number.isFinite(max) || max <= 0) return setError('max trade > 0')
    if (!Number.isFinite(total) || total < max) return setError('budget must be >= max trade')
    if (Number.isFinite(maxHold) && maxHold > 0 && maxHold < 5) {
      return setError('max hold must be >= 5s (or empty to disable)')
    }
    // Note: we used to require at least one exit condition. Removed — if you
    // leave TP/SL/max-hold all empty, the bot just keeps buying until budget
    // is spent and holds until you click Stop & drain or 🚨. The watchdog
    // still acts as a safety net if the page goes down.

    setBusy(true)
    try {
      // 24h hard safety cap on the session — actual end is position-driven
      // (the strategy runner exits when graceful-stop is requested AND all
      // open positions are sold).
      const policy = await window.api.wallet.session.start({
        strategy,
        maxTradeSol: max,
        totalBudgetSol: total,
        durationSec: 24 * 60 * 60,
        allowedActions: allowedActions() as ('swap' | 'transfer' | 'pumpfun_buy' | 'pumpfun_sell')[],
      })
      const watchlistArr = watchlist
        .split(/[\s,]+/).map((s) => s.trim()).filter(Boolean)
      const targetsArr = targetWallets
        .split(/[\s,]+/).map((s) => s.trim()).filter(Boolean)

      const body = {
        strategy,
        policy_id: policy.id,
        max_trade_sol: max,
        total_budget_sol: total,
        expires_at: Math.floor(policy.expiresAt / 1000),
        interval_sec: interval,
        watchlist: watchlistArr,
        target_wallets: targetsArr,
        copy_ratio: parseFloat(copyRatio) || 0.01,
        rug_score_max: parseFloat(rugScoreMax) || 0.5,
        min_liquidity_sol: parseFloat(minLiquiditySol) || 5,
        max_buy_sol: parseFloat(maxBuySol) || max,
        // Exit strategy: server expects fractions (0.5 = 50%); null disables.
        take_profit_pct: Number.isFinite(tpPct) && tpPct > 0 ? tpPct / 100 : null,
        stop_loss_pct: Number.isFinite(slPct) && slPct > 0 ? slPct / 100 : null,
        max_hold_time: Number.isFinite(maxHold) && maxHold > 0 ? maxHold : null,
      }
      const r = await fetch('http://localhost:8902/api/auto/start', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!r.ok) {
        const txt = await r.text()
        // Roll back the session if strategy refused.
        await window.api.wallet.session.end()
        throw new Error(`strategy /auto/start failed: ${txt}`)
      }
      setEvents([])
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function handleStopGraceful(): Promise<void> {
    setBusy(true)
    try {
      // No new buys; runner keeps ticking and selling existing positions
      // until the position list is empty, then exits naturally.
      try { await fetch('http://localhost:8902/api/auto/stop-graceful', { method: 'POST' }) } catch { /* */ }
    } finally {
      setBusy(false)
    }
  }

  async function handlePanicSell(): Promise<void> {
    setBusy(true)
    try {
      const result = await window.api.wallet.panicSell()
      if (!result.ok) {
        setError(result.error ?? 'panic-sell failed')
      } else if (!result.drained) {
        setError(`panic-sell timed out after ${Math.round((result.waitedMs ?? 0) / 1000)}s — ${result.openCount ?? '?'} positions may still be open`)
      }
    } finally {
      setBusy(false)
    }
  }

  async function handleStopForce(): Promise<void> {
    setBusy(true)
    try {
      try { await fetch('http://localhost:8902/api/auto/stop', { method: 'POST' }) } catch { /* */ }
      await window.api.wallet.session.end()
    } finally {
      setBusy(false)
    }
  }

  const remainingSol = session ? session.totalBudgetSol - session.spentSol : 0
  const pctSpent = session ? Math.min(100, (session.spentSol / session.totalBudgetSol) * 100) : 0

  return (
    <div className="trade-panel">
      <div className="trade-panel-title" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span>AUTONOMOUS TRADING</span>
        {session && !panic.active && (
          <span className="watchdog-pill watchdog-active" title="UI heartbeat reaching the watchdog every 5s">
            ● watchdog active
          </span>
        )}
        {panic.active && (
          <span className="watchdog-pill watchdog-panic" title={`Panic reason: ${panic.reason ?? 'unknown'}`}>
            ⚠ PANIC: {panic.reason ?? 'firing'}
          </span>
        )}
      </div>
      {onDevnet && !session && (
        <p className="wallet-subtitle wallet-error" style={{ textAlign: 'left' }}>
          Auto-trade needs mainnet (Jupiter / Pump.fun aren&apos;t deployed on devnet).
          Switch network on the Wallet page first.
        </p>
      )}
      {!traderRunning && !session && (
        <p className="wallet-subtitle" style={{ textAlign: 'left' }}>
          Trader service must be running before you can start an auto-trade session.
        </p>
      )}

      {sessionLost && (
        <div className="wallet-error" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div>
            <strong>Session lost mid-trade.</strong> The signer rejected with
            &quot;no active session&quot;. {sessionLost.stuck.length > 0
              ? `${sessionLost.stuck.length} position(s) are still held on-chain and need to be sold.`
              : 'No open positions are stuck.'}
          </div>
          {sessionLost.stuck.length > 0 && (
            <div style={{ fontSize: 11, color: 'rgba(180,220,180,0.7)', wordBreak: 'break-all' }}>
              Stuck: {sessionLost.stuck.join(', ')}
            </div>
          )}
          <div className="wallet-actions">
            {sessionLost.stuck.length > 0 ? (
              <button
                className="wallet-btn-primary"
                disabled={busy}
                onClick={async () => {
                  setBusy(true)
                  try {
                    // Mint a fresh session policy with budget = sum of stuck
                    // entry SOL + a small buffer for sell-side priority fees.
                    const max = parseFloat(maxTradeSol) || 0.01
                    const policy = await window.api.wallet.session.start({
                      strategy,
                      maxTradeSol: max,
                      totalBudgetSol: Math.max(parseFloat(totalBudgetSol) || 0.05, 0.01),
                      durationSec: 24 * 60 * 60,
                      allowedActions: ['pumpfun_sell', 'pumpfun_buy', 'swap'],
                    })
                    const r = await fetch('http://localhost:8902/api/auto/resume', {
                      method: 'POST',
                      headers: { 'content-type': 'application/json' },
                      body: JSON.stringify({ policy_id: policy.id }),
                    })
                    if (!r.ok) throw new Error(await r.text())
                    setSessionLost(null)
                  } catch (e) {
                    setError((e as Error).message)
                  } finally {
                    setBusy(false)
                  }
                }}
              >
                {busy ? 'Authorizing…' : 'Resume & sell stuck positions (Touch ID)'}
              </button>
            ) : null}
            <button
              className="wallet-btn-secondary"
              onClick={() => setSessionLost(null)}
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {!session && (
        <>
          <label className="trade-label">Strategy</label>
          <div className="trade-tabs" style={{ alignSelf: 'flex-start' }}>
            <button
              className={`trade-tab ${strategy === 'indicator' ? 'active' : ''}`}
              onClick={() => setStrategy('indicator')}
            >
              Indicator
            </button>
            <button
              className={`trade-tab ${strategy === 'copy_trade' ? 'active' : ''}`}
              onClick={() => setStrategy('copy_trade')}
            >
              Copy-trade
            </button>
            <button
              className={`trade-tab ${strategy === 'pumpfun_snipe' ? 'active' : ''}`}
              onClick={() => setStrategy('pumpfun_snipe')}
            >
              Pump.fun snipe
            </button>
          </div>

          {strategy === 'indicator' && (
            <>
              <label className="trade-label">Watchlist (mints, comma or space separated)</label>
              <textarea
                className="wallet-textarea"
                rows={2}
                value={watchlist}
                onChange={(e) => setWatchlist(e.target.value)}
              />
            </>
          )}
          {strategy === 'copy_trade' && (
            <>
              <label className="trade-label">Target wallets</label>
              <textarea
                className="wallet-textarea"
                rows={2}
                value={targetWallets}
                onChange={(e) => setTargetWallets(e.target.value)}
                placeholder="paste one or more whale wallet addresses"
              />
              <label className="trade-label">Copy ratio (0–1, e.g. 0.01 = 1% of whale&apos;s size)</label>
              <input className="wallet-input" value={copyRatio} onChange={(e) => setCopyRatio(e.target.value)} />
            </>
          )}
          {strategy === 'pumpfun_snipe' && (
            <div className="trade-row">
              <div className="trade-col">
                <label className="trade-label">Rug score max (0–1)</label>
                <input className="wallet-input" value={rugScoreMax} onChange={(e) => setRugScoreMax(e.target.value)} />
              </div>
              <div className="trade-col">
                <label className="trade-label">Min liquidity (SOL)</label>
                <input
                  className="wallet-input"
                  value={minLiquiditySol}
                  onChange={(e) => setMinLiquiditySol(e.target.value)}
                />
              </div>
              <div className="trade-col">
                <label className="trade-label">Max buy (SOL)</label>
                <input className="wallet-input" value={maxBuySol} onChange={(e) => setMaxBuySol(e.target.value)} />
              </div>
            </div>
          )}

          <div className="trade-row">
            <div className="trade-col">
              <label className="trade-label">Max per trade (SOL)</label>
              <input
                className="wallet-input"
                value={maxTradeSol}
                onChange={(e) => setMaxTradeSol(e.target.value)}
              />
            </div>
            <div className="trade-col">
              <label className="trade-label">Total budget (SOL)</label>
              <input
                className="wallet-input"
                value={totalBudgetSol}
                onChange={(e) => setTotalBudgetSol(e.target.value)}
              />
            </div>
          </div>
          <div className="trade-result-label" style={{ marginTop: 6 }}>EXIT STRATEGY</div>
          <div className="trade-row">
            <div className="trade-col">
              <label className="trade-label">Take profit (%)</label>
              <input
                className="wallet-input"
                value={takeProfitPct}
                onChange={(e) => setTakeProfitPct(e.target.value)}
                placeholder="50"
              />
            </div>
            <div className="trade-col">
              <label className="trade-label">Stop loss (%)</label>
              <input
                className="wallet-input"
                value={stopLossPct}
                onChange={(e) => setStopLossPct(e.target.value)}
                placeholder="30"
              />
            </div>
            <div className="trade-col">
              <label className="trade-label">Max hold (seconds, optional)</label>
              <input
                className="wallet-input"
                value={maxHoldSec}
                onChange={(e) => setMaxHoldSec(e.target.value)}
                placeholder="(empty = hold until you stop)"
              />
            </div>
          </div>
          <div className="trade-row">
            <div className="trade-col">
              <label className="trade-label">Tick interval (seconds)</label>
              <input
                className="wallet-input"
                value={intervalSec}
                onChange={(e) => setIntervalSec(e.target.value)}
              />
            </div>
          </div>

          <p className="wallet-subtitle" style={{ textAlign: 'left', fontSize: 11, color: 'rgba(180,220,180,0.55)' }}>
            Position-based session. Exits use chainstacklabs/pumpfun-bonkfun-bot
            semantics: first of take-profit / stop-loss / max-hold to fire wins.
            Live price comes from pump.fun&apos;s public bonding-curve endpoint.
            <strong> Max-hold is optional</strong> — leave it empty and positions
            stay open until TP or SL fires, you click <em>Stop &amp; drain</em>,
            or you hit <em>🚨 Sell everything now</em>. Leaving TP/SL empty too
            puts the bot in pure manual mode (only Stop or 🚨 will close).
          </p>

          {error && <div className="wallet-error">{error}</div>}

          <div className="wallet-actions">
            <button
              className="wallet-btn-primary"
              disabled={busy || !traderRunning || onDevnet}
              onClick={handleStart}
            >
              {busy ? 'Starting…' : onDevnet ? 'Start (mainnet only)' : 'Start (Touch ID)'}
            </button>
          </div>
        </>
      )}

      {session && (
        <div className="auto-active">
          <div className="trade-result-section">
            <div className="trade-result-label">ACTIVE SESSION</div>
            <div className="trade-result-text">
              {session.strategy} · started {new Date(session.startedAt).toLocaleTimeString()} ·
              expires {new Date(session.expiresAt).toLocaleTimeString()}
            </div>
          </div>

          <div className="budget-bar-wrap">
            <div className="budget-bar-label">
              spent {session.spentSol.toFixed(4)} / {session.totalBudgetSol} SOL
              · remaining {remainingSol.toFixed(4)}
            </div>
            <div className="budget-bar"><div className="budget-bar-fill" style={{ width: `${pctSpent}%` }} /></div>
          </div>

          <div className="wallet-actions">
            <button className="wallet-btn-primary" disabled={busy} onClick={handleStopGraceful}>
              {busy ? 'Stopping…' : 'Stop & drain positions'}
            </button>
            <button
              className="wallet-btn-danger"
              disabled={busy || openCount === 0}
              onClick={handlePanicSell}
              title="Bypass TP/SL/hold-time and sell every open position now"
            >
              {busy ? 'Selling…' : `🚨 Sell everything now${openCount > 0 ? ` (${openCount})` : ''}`}
            </button>
            <button className="wallet-btn-secondary" disabled={busy} onClick={handleStopForce}>
              Force stop
            </button>
          </div>

          <div className="auto-feed">
            {events.length === 0 ? (
              <div className="auto-row">waiting for first decision…</div>
            ) : (
              [...events].reverse().slice(0, 50).map((ev, i) => (
                <div className={`auto-row auto-row-${ev.kind}`} key={`${ev.ts}-${i}`}>
                  <span className="auto-row-time">
                    {new Date(ev.ts * 1000).toLocaleTimeString()}
                  </span>
                  <span className="auto-row-kind">{ev.kind}</span>
                  <span className="auto-row-payload">
                    {Object.entries(ev)
                      .filter(([k]) => k !== 'ts' && k !== 'kind')
                      .map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
                      .join(' · ')}
                  </span>
                </div>
              ))
            )}
          </div>

          <PositionsPanel positions={positions} />
        </div>
      )}
    </div>
  )
}

// ── Positions panel ──────────────────────────────────────────────────────────
// Visual list of currently-held positions below the activity feed. Updated
// every 3s from /api/auto/status. Each card shows entry price, age, TP/SL
// targets, and a status pill (holding / selling / error).

function fmtPrice(p: number | null | undefined): string {
  if (!p || !Number.isFinite(p)) return '—'
  if (p >= 0.01) return p.toFixed(6)
  if (p >= 1e-6) return p.toExponential(3)
  return p.toExponential(2)
}

function fmtAge(sec: number): string {
  if (sec < 60) return `${Math.round(sec)}s`
  if (sec < 3600) return `${Math.floor(sec / 60)}m ${Math.round(sec % 60)}s`
  return `${Math.floor(sec / 3600)}h ${Math.floor((sec % 3600) / 60)}m`
}

function shortMint(m: string): string {
  return m.length > 14 ? `${m.slice(0, 6)}…${m.slice(-4)}` : m
}

function positionStatus(p: OpenPosition): { label: string; cls: string } {
  if (p.last_error) return { label: 'error', cls: 'pos-status-error' }
  if (p.sell_attempted) return { label: 'selling', cls: 'pos-status-selling' }
  return { label: 'holding', cls: 'pos-status-holding' }
}

function PositionsPanel({ positions }: { positions: OpenPosition[] }): React.JSX.Element | null {
  if (positions.length === 0) return null
  return (
    <div className="positions-panel">
      <div className="trade-result-label">
        OPEN POSITIONS · {positions.length}
      </div>
      <div className="positions-grid">
        {positions.map((p) => {
          const status = positionStatus(p)
          const holdLeft = p.max_hold_time != null
            ? Math.max(0, p.max_hold_time - p.age_sec)
            : null
          return (
            <div key={p.mint} className="position-card">
              <div className="position-head">
                <span className="position-symbol">{p.symbol || shortMint(p.mint)}</span>
                <span className={`position-status-pill ${status.cls}`}>{status.label}</span>
              </div>
              <div className="position-mint" title={p.mint}>{shortMint(p.mint)}</div>
              <div className="position-row">
                <span className="position-label">entry</span>
                <span>{p.entry_sol.toFixed(4)} SOL</span>
                <span className="position-faint">@ {fmtPrice(p.entry_price)}</span>
              </div>
              <div className="position-row">
                <span className="position-label">age</span>
                <span>{fmtAge(p.age_sec)}</span>
                {holdLeft !== null && (
                  <span className="position-faint">
                    · {fmtAge(holdLeft)} until forced sell
                  </span>
                )}
              </div>
              <div className="position-targets">
                {p.take_profit_price != null && (
                  <span className="position-target tp">
                    TP {fmtPrice(p.take_profit_price)}
                  </span>
                )}
                {p.stop_loss_price != null && (
                  <span className="position-target sl">
                    SL {fmtPrice(p.stop_loss_price)}
                  </span>
                )}
                {p.take_profit_price == null && p.stop_loss_price == null && p.max_hold_time == null && (
                  <span className="position-faint">manual exit only</span>
                )}
              </div>
              {p.last_error && (
                <div className="position-error" title={p.last_error}>
                  {p.last_error}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function SpawnPanel({
  title,
  status,
  installing,
  installLog,
  installLabel,
  notInstalledHint,
  onInstall,
  onRestart,
}: {
  title: string
  status: AgentStatus | null
  installing: boolean
  installLog: string[]
  installLabel: string
  notInstalledHint: string
  onInstall: () => void
  onRestart: () => void
}): React.JSX.Element | null {
  if (!status) return null
  if (status.state === 'running') return null

  const tail = status.logTail.slice(-12)
  const label = title.toLowerCase().split(' ')[0]

  return (
    <div className="trade-panel spawn-panel">
      <div className="trade-panel-title">{title} · {status.state}</div>

      {status.state === 'not-installed' && (
        <>
          <p className="wallet-subtitle" style={{ textAlign: 'left' }}>
            {notInstalledHint}
          </p>
          <div className="wallet-actions">
            <button
              className="wallet-btn-primary"
              disabled={installing}
              onClick={onInstall}
            >
              {installing ? 'Installing…' : installLabel}
            </button>
          </div>
        </>
      )}

      {status.state === 'spawning' && (
        <p className="wallet-subtitle" style={{ textAlign: 'left' }}>
          Starting {label} on :{status.port}…
        </p>
      )}

      {(status.state === 'crashed' || status.state === 'stopped') && (
        <>
          <p
            className={`wallet-subtitle ${status.state === 'crashed' ? 'wallet-error' : ''}`}
            style={{ textAlign: 'left' }}
          >
            {status.state === 'crashed'
              ? `${label} crashed: ${status.lastError ?? 'unknown'}`
              : `${label} is stopped. Lock+unlock the wallet, or restart manually.`}
          </p>
          <div className="wallet-actions">
            <button className="wallet-btn-primary" onClick={onRestart}>
              Restart {label}
            </button>
            <button className="wallet-btn-secondary" disabled={installing} onClick={onInstall}>
              {installing ? 'Installing…' : installLabel}
            </button>
          </div>
        </>
      )}

      {(installing || installLog.length > 0) && (
        <pre className="trade-pre spawn-log">{installLog.join('\n')}</pre>
      )}

      {tail.length > 0 && (
        <details>
          <summary className="trade-label" style={{ cursor: 'pointer' }}>
            log tail (last {tail.length})
          </summary>
          <pre className="trade-pre spawn-log">{tail.join('\n')}</pre>
        </details>
      )}
    </div>
  )
}

function SignatureToast({
  signature,
  network,
}: {
  signature: string
  network: string | undefined
}): React.JSX.Element {
  const url =
    network === 'devnet'
      ? `https://solscan.io/tx/${signature}?cluster=devnet`
      : `https://solscan.io/tx/${signature}`
  return (
    <div className="wallet-toast wallet-toast-success">
      <span>Sent ·</span>
      <a href={url} target="_blank" rel="noreferrer">
        {SHORT(signature, 10)}
      </a>
    </div>
  )
}
