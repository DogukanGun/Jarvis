import { useCallback, useEffect, useState } from 'react'

type Network = 'mainnet' | 'devnet'

interface TokenHolding {
  mint: string
  amount: string
  uiAmount: number
  decimals: number
  tokenAccount: string
  programId: string
}

interface WalletStatus {
  hasVault: boolean
  isUnlocked: boolean
  publicKey: string | null
  config: { network: Network; rpcUrl: string; explorerBase: string; autoLockSeconds: number }
}

interface Props {
  onLocked: () => void
  onOpenChat: () => void
  onOpenTrade: () => void
}

type SendDraft = { to: string; amount: string; mint: string | null }

const SHORT = (s: string, n = 6): string => `${s.slice(0, n)}…${s.slice(-4)}`

export default function Wallet({ onLocked, onOpenChat, onOpenTrade }: Props): React.JSX.Element {
  const [status, setStatus] = useState<WalletStatus | null>(null)
  const [solBalance, setSolBalance] = useState<number | null>(null)
  const [holdings, setHoldings] = useState<TokenHolding[]>([])
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [faucetUrl, setFaucetUrl] = useState<string | null>(null)
  const [draft, setDraft] = useState<SendDraft | null>(null)
  const [sendBusy, setSendBusy] = useState(false)
  const [sendResult, setSendResult] = useState<{ signature: string; explorerBase: string } | null>(null)
  const [addrCopied, setAddrCopied] = useState(false)
  const [exportOpen, setExportOpen] = useState(false)
  const [exportPin, setExportPin] = useState('')
  const [exportBusy, setExportBusy] = useState(false)
  const [exportError, setExportError] = useState('')
  const [exportedBase58, setExportedBase58] = useState<string | null>(null)
  const [exportedArray, setExportedArray] = useState<number[] | null>(null)
  const [exportFormat, setExportFormat] = useState<'base58' | 'array'>('base58')
  const [exportCopied, setExportCopied] = useState(false)

  async function copyAddress(): Promise<void> {
    if (!status?.publicKey) return
    try {
      await window.api.copyText(status.publicKey)
    } catch {
      try { await navigator.clipboard.writeText(status.publicKey) } catch { /* both failed */ }
    }
    setAddrCopied(true)
    setTimeout(() => setAddrCopied(false), 1600)
  }

  const refresh = useCallback(async () => {
    setRefreshing(true)
    setError(null)
    try {
      const s = await window.api.wallet.status()
      setStatus(s)
      if (!s.isUnlocked) {
        onLocked()
        return
      }
      const bal = await window.api.wallet.getBalance()
      setSolBalance(bal.sol.sol)
      setHoldings(bal.holdings)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setRefreshing(false)
    }
  }, [onLocked])

  useEffect(() => {
    void refresh()
    const off = window.api.wallet.onLockChange((unlocked) => {
      if (!unlocked) onLocked()
    })
    return () => off()
  }, [refresh, onLocked])

  async function handleNetworkSwitch(net: Network): Promise<void> {
    await window.api.wallet.setConfig({ network: net })
    await refresh()
  }

  async function handleAirdrop(): Promise<void> {
    setError(null)
    setFaucetUrl(null)
    try {
      // 0.5 SOL is far more likely to land than 1+ on the public faucet.
      const result = await window.api.wallet.airdrop(0.5)
      if (result.ok) {
        await refresh()
      } else {
        setError(result.error ?? 'airdrop failed')
        if (result.code === 'DEVNET_FAUCET_RATE_LIMIT' && result.webFaucetUrl) {
          setFaucetUrl(result.webFaucetUrl)
        }
      }
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function openWebFaucet(): Promise<void> {
    if (!status?.publicKey) return
    const url = faucetUrl ?? `https://faucet.solana.com/?walletAddress=${status.publicKey}&amount=0.5`
    try { await window.api.copyText(status.publicKey) } catch { /* */ }
    await window.api.openExternal(url)
  }

  function closeExport(): void {
    setExportOpen(false)
    setExportPin('')
    setExportError('')
    setExportedBase58(null)
    setExportedArray(null)
    setExportCopied(false)
  }

  async function handleExport(): Promise<void> {
    if (!exportPin) return setExportError('PIN required')
    setExportBusy(true)
    setExportError('')
    try {
      const result = await window.api.wallet.exportPrivateKey(exportPin)
      if (!result.ok) {
        setExportError(result.error ?? 'Export failed')
        setExportPin('')
        return
      }
      setExportedBase58(result.base58 ?? null)
      setExportedArray(result.array ?? null)
      setExportPin('')
    } catch (e) {
      setExportError((e as Error).message)
    } finally {
      setExportBusy(false)
    }
  }

  async function copyExported(): Promise<void> {
    const text = exportFormat === 'base58'
      ? exportedBase58 ?? ''
      : JSON.stringify(exportedArray ?? [])
    if (!text) return
    try {
      await window.api.copyText(text)
    } catch {
      try { await navigator.clipboard.writeText(text) } catch { /* */ }
    }
    setExportCopied(true)
    setTimeout(() => setExportCopied(false), 1600)
  }

  async function handleLock(): Promise<void> {
    await window.api.wallet.lock()
    onLocked()
  }

  async function handleSend(): Promise<void> {
    if (!draft) return
    const amount = parseFloat(draft.amount)
    if (!Number.isFinite(amount) || amount <= 0) {
      setError('Invalid amount')
      return
    }
    if (!draft.to || draft.to.length < 32) {
      setError('Invalid recipient')
      return
    }
    setSendBusy(true)
    setError(null)
    try {
      const result = draft.mint
        ? await window.api.wallet.sendSpl(draft.to, draft.mint, amount)
        : await window.api.wallet.sendSol(draft.to, amount)
      setSendResult(result)
      setDraft(null)
      await refresh()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSendBusy(false)
    }
  }

  if (!status?.publicKey) {
    return (
      <div className="wallet-page">
        <div className="wallet-loading">Loading wallet…</div>
      </div>
    )
  }

  const network = status.config.network
  const explorerUrl = (sig: string): string =>
    network === 'devnet'
      ? `https://solscan.io/tx/${sig}?cluster=devnet`
      : `https://solscan.io/tx/${sig}`

  return (
    <div className="wallet-page">
      <div className="wallet-topbar">
        <div className="wallet-network-toggle">
          <button
            className={`wallet-net-btn ${network === 'devnet' ? 'active' : ''}`}
            onClick={() => handleNetworkSwitch('devnet')}
          >
            devnet
          </button>
          <button
            className={`wallet-net-btn ${network === 'mainnet' ? 'active' : ''}`}
            onClick={() => handleNetworkSwitch('mainnet')}
          >
            mainnet
          </button>
        </div>
        <div className="wallet-topbar-actions">
          <button className="wallet-btn-secondary wallet-btn-sm" onClick={onOpenChat}>Chat</button>
          <button className="wallet-btn-secondary wallet-btn-sm" onClick={onOpenTrade}>Trade</button>
          <button
            className="wallet-btn-secondary wallet-btn-sm"
            onClick={() => setExportOpen(true)}
          >
            Export
          </button>
          <button className="wallet-btn-secondary wallet-btn-sm" onClick={handleLock}>Lock</button>
        </div>
      </div>

      {network === 'devnet' && (
        <div className="trade-devnet-banner" style={{ margin: '0 0 4px' }}>
          <strong>Devnet:</strong> only SOL/SPL transfers work here.
          Jupiter swap, Pump.fun, and auto-trade need <em>mainnet</em> — toggle above when you&apos;re ready.
        </div>
      )}

      <div className="wallet-balance-card">
        <div className="wallet-balance-label">SOL BALANCE · {network}</div>
        <div className="wallet-balance-amount">
          {solBalance !== null ? solBalance.toFixed(4) : '—'} <span className="wallet-balance-unit">SOL</span>
        </div>
        <div className="wallet-address-row">
          <code className="wallet-address">{status.publicKey}</code>
          <button className="wallet-btn-link" onClick={copyAddress}>
            {addrCopied ? 'copied ✓' : 'copy'}
          </button>
        </div>
        <div className="wallet-balance-actions">
          <button className="wallet-btn-primary" onClick={() => setDraft({ to: '', amount: '', mint: null })}>
            Send
          </button>
          <button className="wallet-btn-secondary" onClick={() => void refresh()} disabled={refreshing}>
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
          {network === 'devnet' && (
            <>
              <button className="wallet-btn-secondary" onClick={handleAirdrop}>
                Airdrop 0.5 SOL
              </button>
              <button className="wallet-btn-secondary" onClick={openWebFaucet}>
                Web faucet
              </button>
            </>
          )}
        </div>
      </div>

      <div className="wallet-section">
        <div className="wallet-section-title">SPL TOKENS</div>
        {holdings.length === 0 ? (
          <div className="wallet-empty">No SPL holdings on this network.</div>
        ) : (
          <div className="wallet-token-list">
            {holdings.map((h) => (
              <div className="wallet-token-row" key={h.tokenAccount}>
                <div className="wallet-token-mint">{SHORT(h.mint, 8)}</div>
                <div className="wallet-token-amount">{h.uiAmount}</div>
                <button
                  className="wallet-btn-link"
                  onClick={() => setDraft({ to: '', amount: '', mint: h.mint })}
                >send</button>
              </div>
            ))}
          </div>
        )}
      </div>

      {error && (
        <div className="wallet-error">
          {error}
          {faucetUrl && (
            <div style={{ marginTop: 8 }}>
              <button className="wallet-btn-primary" onClick={openWebFaucet}>
                Open web faucet (address copied)
              </button>
            </div>
          )}
        </div>
      )}

      {sendResult && (
        <div className="wallet-toast wallet-toast-success">
          <span>Sent ·</span>
          <a
            href={explorerUrl(sendResult.signature)}
            target="_blank"
            rel="noreferrer"
          >
            {SHORT(sendResult.signature, 10)}
          </a>
          <button className="wallet-btn-link" onClick={() => setSendResult(null)}>dismiss</button>
        </div>
      )}

      {exportOpen && (
        <div className="wallet-modal-backdrop" onClick={() => !exportBusy && closeExport()}>
          <div className="wallet-modal" onClick={(e) => e.stopPropagation()}>
            <div className="wallet-modal-title">EXPORT PRIVATE KEY</div>

            {!exportedBase58 ? (
              <>
                <p className="wallet-subtitle wallet-error" style={{ textAlign: 'left', margin: 0 }}>
                  Anyone with this key can drain your wallet. Never paste it into a website,
                  Telegram chat, Discord DM, or screenshot it. We require Touch ID + your wallet PIN.
                </p>
                <input
                  className="wallet-input"
                  type="password"
                  placeholder="Wallet PIN"
                  value={exportPin}
                  onChange={(e) => { setExportPin(e.target.value); setExportError('') }}
                  onKeyDown={(e) => e.key === 'Enter' && handleExport()}
                  autoFocus
                />
                {exportError && <p className="wallet-error">{exportError}</p>}
                <div className="wallet-actions">
                  <button
                    className="wallet-btn-secondary"
                    disabled={exportBusy}
                    onClick={closeExport}
                  >
                    Cancel
                  </button>
                  <button
                    className="wallet-btn-danger"
                    disabled={exportBusy || exportPin.length < 4}
                    onClick={handleExport}
                  >
                    {exportBusy ? 'Verifying…' : 'Reveal with Touch ID'}
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className="wallet-subtitle" style={{ textAlign: 'left', margin: 0 }}>
                  Private key revealed. This window will not retain it after close.
                </p>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    className={`wallet-btn-secondary wallet-btn-sm ${exportFormat === 'base58' ? 'active' : ''}`}
                    onClick={() => setExportFormat('base58')}
                    style={{ opacity: exportFormat === 'base58' ? 1 : 0.5 }}
                  >
                    base58 (Solana CLI / Solflare)
                  </button>
                  <button
                    className={`wallet-btn-secondary wallet-btn-sm ${exportFormat === 'array' ? 'active' : ''}`}
                    onClick={() => setExportFormat('array')}
                    style={{ opacity: exportFormat === 'array' ? 1 : 0.5 }}
                  >
                    byte array (Phantom)
                  </button>
                </div>
                <pre className="trade-pre" style={{ maxHeight: 160, fontSize: 11 }}>
                  {exportFormat === 'base58'
                    ? exportedBase58
                    : JSON.stringify(exportedArray)}
                </pre>
                <div className="wallet-actions">
                  <button className="wallet-btn-secondary" onClick={copyExported}>
                    {exportCopied ? 'Copied ✓' : 'Copy'}
                  </button>
                  <button className="wallet-btn-primary" onClick={closeExport}>
                    Done
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {draft && (
        <div className="wallet-modal-backdrop" onClick={() => !sendBusy && setDraft(null)}>
          <div className="wallet-modal" onClick={(e) => e.stopPropagation()}>
            <div className="wallet-modal-title">
              SEND {draft.mint ? `TOKEN ${SHORT(draft.mint, 6)}` : 'SOL'}
            </div>
            <input
              className="wallet-input"
              placeholder="Recipient address"
              value={draft.to}
              onChange={(e) => setDraft({ ...draft, to: e.target.value })}
              autoFocus
            />
            <input
              className="wallet-input"
              placeholder={draft.mint ? 'Amount' : 'Amount in SOL'}
              value={draft.amount}
              onChange={(e) => setDraft({ ...draft, amount: e.target.value })}
              inputMode="decimal"
            />
            <div className="wallet-actions">
              <button
                className="wallet-btn-secondary"
                disabled={sendBusy}
                onClick={() => setDraft(null)}
              >Cancel</button>
              <button
                className="wallet-btn-primary"
                disabled={sendBusy}
                onClick={handleSend}
              >
                {sendBusy ? 'Signing…' : 'Confirm with Touch ID'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
