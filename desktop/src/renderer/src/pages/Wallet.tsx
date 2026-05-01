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
  const [draft, setDraft] = useState<SendDraft | null>(null)
  const [sendBusy, setSendBusy] = useState(false)
  const [sendResult, setSendResult] = useState<{ signature: string; explorerBase: string } | null>(null)
  const [addrCopied, setAddrCopied] = useState(false)

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
    try {
      // 0.5 SOL is far more likely to land than 1+ on the public faucet.
      await window.api.wallet.airdrop(0.5)
      await refresh()
    } catch (e) {
      setError((e as Error).message)
    }
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
          <button className="wallet-btn-secondary wallet-btn-sm" onClick={handleLock}>Lock</button>
        </div>
      </div>

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
            <button className="wallet-btn-secondary" onClick={handleAirdrop}>
              Airdrop 0.5 SOL
            </button>
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

      {error && <div className="wallet-error">{error}</div>}

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
