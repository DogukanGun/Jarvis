import { useEffect, useState } from 'react'

interface Props {
  onUnlocked: () => void
  onWipe: () => void
}

export default function WalletUnlock({ onUnlocked, onWipe }: Props): React.JSX.Element {
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [publicKey, setPublicKey] = useState<string | null>(null)
  const [confirmingWipe, setConfirmingWipe] = useState(false)

  useEffect(() => {
    void window.api.wallet.status().then((s) => setPublicKey(s.publicKey))
  }, [])

  async function handleUnlock(): Promise<void> {
    setError('')
    setBusy(true)
    try {
      const result = await window.api.wallet.unlock(pin)
      if (result.ok) {
        onUnlocked()
      } else {
        setError(result.error ?? 'Wrong PIN')
        setPin('')
      }
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function handleWipe(): Promise<void> {
    setBusy(true)
    try {
      await window.api.wallet.wipe()
      onWipe()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="wallet-setup">
      <h2 className="wallet-title">UNLOCK WALLET</h2>
      {publicKey && (
        <p className="wallet-subtitle">
          <code>{publicKey.slice(0, 8)}…{publicKey.slice(-6)}</code>
        </p>
      )}
      <input
        className="wallet-input"
        type="password"
        placeholder="Wallet PIN"
        value={pin}
        onChange={(e) => { setPin(e.target.value); setError('') }}
        onKeyDown={(e) => e.key === 'Enter' && handleUnlock()}
        autoFocus
      />
      {error && <p className="wallet-error">{error}</p>}
      <div className="wallet-actions">
        <button className="wallet-btn-primary" disabled={busy || pin.length < 4} onClick={handleUnlock}>
          {busy ? 'Unlocking…' : 'Unlock'}
        </button>
      </div>
      {!confirmingWipe ? (
        <button className="wallet-btn-link wallet-danger" onClick={() => setConfirmingWipe(true)}>
          Forgot PIN · wipe wallet
        </button>
      ) : (
        <div className="wallet-wipe-confirm">
          <p className="wallet-error">
            This will permanently delete the encrypted keypair on this device.
            You can only recover with your seed phrase.
          </p>
          <div className="wallet-actions">
            <button className="wallet-btn-secondary" disabled={busy} onClick={() => setConfirmingWipe(false)}>
              Cancel
            </button>
            <button className="wallet-btn-danger" disabled={busy} onClick={handleWipe}>
              {busy ? 'Wiping…' : 'Wipe with Touch ID'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
