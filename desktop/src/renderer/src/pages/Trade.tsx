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

      {tab === 'auto' && <AutoTradeTab traderRunning={!!health.ok} />}
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

function AutoTradeTab({ traderRunning }: { traderRunning: boolean }): React.JSX.Element {
  const [strategy, setStrategy] = useState<AutoStrategyKey>('indicator')
  const [maxTradeSol, setMaxTradeSol] = useState('0.01')
  const [totalBudgetSol, setTotalBudgetSol] = useState('0.05')
  const [durationMin, setDurationMin] = useState('15')
  const [intervalSec, setIntervalSec] = useState('30')

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
  const esRef = useRef<EventSource | null>(null)

  // Subscribe to session changes from main.
  useEffect(() => {
    void window.api.wallet.session.status().then(setSession)
    const off = window.api.wallet.session.onChange(setSession)
    return () => off()
  }, [])

  // SSE subscription to strategy events while a session is active.
  useEffect(() => {
    if (!session) {
      if (esRef.current) {
        esRef.current.close()
        esRef.current = null
      }
      return
    }
    if (esRef.current) return
    const es = new EventSource('http://localhost:8902/api/auto/events')
    esRef.current = es
    es.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data) as AutoEvent
        setEvents((prev) => [...prev.slice(-300), ev])
      } catch { /* ignore */ }
    }
    es.onerror = () => {
      // strategy died or stream cut — leave silently
    }
    return () => {
      es.close()
      esRef.current = null
    }
  }, [session])

  const allowedActions = (): string[] => {
    if (strategy === 'indicator' || strategy === 'copy_trade') return ['swap']
    return ['pumpfun_buy', 'pumpfun_sell']
  }

  async function handleStart(): Promise<void> {
    setError(null)
    const max = parseFloat(maxTradeSol)
    const total = parseFloat(totalBudgetSol)
    const durMin = parseInt(durationMin, 10)
    const interval = parseInt(intervalSec, 10)
    if (!Number.isFinite(max) || max <= 0) return setError('max trade > 0')
    if (!Number.isFinite(total) || total < max) return setError('budget must be >= max trade')
    if (!Number.isFinite(durMin) || durMin < 1) return setError('duration must be >= 1 min')

    setBusy(true)
    try {
      const policy = await window.api.wallet.session.start({
        strategy,
        maxTradeSol: max,
        totalBudgetSol: total,
        durationSec: durMin * 60,
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

  async function handleStop(): Promise<void> {
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
      <div className="trade-panel-title">AUTONOMOUS TRADING</div>
      {!traderRunning && !session && (
        <p className="wallet-subtitle" style={{ textAlign: 'left' }}>
          Trader service must be running before you can start an auto-trade session.
        </p>
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
          <div className="trade-row">
            <div className="trade-col">
              <label className="trade-label">Duration (minutes)</label>
              <input
                className="wallet-input"
                value={durationMin}
                onChange={(e) => setDurationMin(e.target.value)}
              />
            </div>
            <div className="trade-col">
              <label className="trade-label">Tick interval (seconds)</label>
              <input
                className="wallet-input"
                value={intervalSec}
                onChange={(e) => setIntervalSec(e.target.value)}
              />
            </div>
          </div>

          {error && <div className="wallet-error">{error}</div>}

          <div className="wallet-actions">
            <button
              className="wallet-btn-primary"
              disabled={busy || !traderRunning}
              onClick={handleStart}
            >
              {busy ? 'Starting…' : 'Start (Touch ID)'}
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
            <button className="wallet-btn-danger" disabled={busy} onClick={handleStop}>
              {busy ? 'Stopping…' : 'STOP NOW'}
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
        </div>
      )}
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
