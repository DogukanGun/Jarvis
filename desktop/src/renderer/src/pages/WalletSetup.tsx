import { useState } from 'react'

type Mode = 'choose' | 'create-pin' | 'show-mnemonic' | 'import-mnemonic' | 'import-base58'

interface Props {
  onReady: () => void
}

export default function WalletSetup({ onReady }: Props): React.JSX.Element {
  const [mode, setMode] = useState<Mode>('choose')
  const [pin, setPin] = useState('')
  const [confirmPin, setConfirmPin] = useState('')
  const [mnemonicInput, setMnemonicInput] = useState('')
  const [base58Input, setBase58Input] = useState('')
  const [generatedMnemonic, setGeneratedMnemonic] = useState<string | null>(null)
  const [generatedPubkey, setGeneratedPubkey] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [pendingAction, setPendingAction] = useState<'generate' | 'mnemonic' | 'base58'>('generate')
  const [copied, setCopied] = useState(false)

  async function copyMnemonic(): Promise<void> {
    if (!generatedMnemonic) return
    try {
      await window.api.copyText(generatedMnemonic)
    } catch {
      try { await navigator.clipboard.writeText(generatedMnemonic) } catch { /* both failed */ }
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  function pinValid(): boolean {
    if (pin.length < 6) {
      setError('PIN must be at least 6 characters')
      return false
    }
    if (pin !== confirmPin) {
      setError('PINs do not match')
      return false
    }
    return true
  }

  async function handleCreate(): Promise<void> {
    if (!pinValid()) return
    setError('')
    setBusy(true)
    try {
      if (pendingAction === 'generate') {
        const result = await window.api.wallet.create({ kind: 'generate' }, pin)
        setGeneratedMnemonic(result.mnemonic)
        setGeneratedPubkey(result.publicKey)
        setMode('show-mnemonic')
      } else if (pendingAction === 'mnemonic') {
        const result = await window.api.wallet.create(
          { kind: 'mnemonic', mnemonic: mnemonicInput },
          pin,
        )
        setGeneratedPubkey(result.publicKey)
        onReady()
      } else {
        const result = await window.api.wallet.create(
          { kind: 'base58', base58: base58Input },
          pin,
        )
        setGeneratedPubkey(result.publicKey)
        onReady()
      }
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  if (mode === 'choose') {
    return (
      <div className="wallet-setup">
        <h2 className="wallet-title">SOLANA WALLET</h2>
        <p className="wallet-subtitle">Local keypair · biometric-gated · stored encrypted on this machine</p>

        <div className="wallet-choice-grid">
          <button
            className="wallet-choice-btn"
            onClick={() => { setPendingAction('generate'); setMode('create-pin') }}
          >
            <div className="wallet-choice-title">Create new wallet</div>
            <div className="wallet-choice-hint">Generate a fresh seed phrase</div>
          </button>
          <button
            className="wallet-choice-btn"
            onClick={() => { setPendingAction('mnemonic'); setMode('import-mnemonic') }}
          >
            <div className="wallet-choice-title">Import seed phrase</div>
            <div className="wallet-choice-hint">12 or 24 words</div>
          </button>
          <button
            className="wallet-choice-btn"
            onClick={() => { setPendingAction('base58'); setMode('import-base58') }}
          >
            <div className="wallet-choice-title">Import private key</div>
            <div className="wallet-choice-hint">Base58 secret key</div>
          </button>
        </div>
      </div>
    )
  }

  if (mode === 'import-mnemonic') {
    return (
      <div className="wallet-setup">
        <h2 className="wallet-title">IMPORT SEED PHRASE</h2>
        <textarea
          className="wallet-textarea"
          rows={3}
          placeholder="word1 word2 word3 …"
          value={mnemonicInput}
          onChange={(e) => { setMnemonicInput(e.target.value); setError('') }}
          autoFocus
        />
        <div className="wallet-actions">
          <button className="wallet-btn-secondary" onClick={() => setMode('choose')}>Back</button>
          <button
            className="wallet-btn-primary"
            disabled={mnemonicInput.trim().split(/\s+/).length < 12}
            onClick={() => setMode('create-pin')}
          >
            Continue
          </button>
        </div>
      </div>
    )
  }

  if (mode === 'import-base58') {
    return (
      <div className="wallet-setup">
        <h2 className="wallet-title">IMPORT PRIVATE KEY</h2>
        <input
          className="wallet-input"
          type="password"
          placeholder="Base58 secret key"
          value={base58Input}
          onChange={(e) => { setBase58Input(e.target.value); setError('') }}
          autoFocus
        />
        <div className="wallet-actions">
          <button className="wallet-btn-secondary" onClick={() => setMode('choose')}>Back</button>
          <button
            className="wallet-btn-primary"
            disabled={base58Input.trim().length < 80}
            onClick={() => setMode('create-pin')}
          >
            Continue
          </button>
        </div>
      </div>
    )
  }

  if (mode === 'create-pin') {
    return (
      <div className="wallet-setup">
        <h2 className="wallet-title">SET WALLET PIN</h2>
        <p className="wallet-subtitle">Used to encrypt your keypair on this device. Min 6 chars.</p>
        <input
          className="wallet-input"
          type="password"
          placeholder="PIN"
          value={pin}
          onChange={(e) => { setPin(e.target.value); setError('') }}
          autoFocus
        />
        <input
          className="wallet-input"
          type="password"
          placeholder="Confirm PIN"
          value={confirmPin}
          onChange={(e) => { setConfirmPin(e.target.value); setError('') }}
          onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
        />
        {error && <p className="wallet-error">{error}</p>}
        <div className="wallet-actions">
          <button className="wallet-btn-secondary" disabled={busy} onClick={() => setMode('choose')}>Back</button>
          <button className="wallet-btn-primary" disabled={busy} onClick={handleCreate}>
            {busy ? 'Encrypting…' : 'Create Wallet'}
          </button>
        </div>
      </div>
    )
  }

  if (mode === 'show-mnemonic' && generatedMnemonic) {
    return (
      <div className="wallet-setup">
        <h2 className="wallet-title">WRITE THIS DOWN</h2>
        <p className="wallet-subtitle">
          Your seed phrase is the only way to recover this wallet.
          Anyone with these words controls your funds. Store it offline.
        </p>
        <div className="wallet-mnemonic-grid">
          {generatedMnemonic.split(' ').map((word, i) => (
            <div className="wallet-mnemonic-cell" key={i}>
              <span className="wallet-mnemonic-idx">{i + 1}</span>
              <span className="wallet-mnemonic-word">{word}</span>
            </div>
          ))}
        </div>
        {generatedPubkey && (
          <p className="wallet-subtitle">Address: <code>{generatedPubkey}</code></p>
        )}
        <div className="wallet-actions">
          <button className="wallet-btn-secondary" onClick={copyMnemonic}>
            {copied ? 'Copied ✓' : 'Copy'}
          </button>
          <button className="wallet-btn-primary" onClick={onReady}>
            I&apos;ve saved it · continue
          </button>
        </div>
      </div>
    )
  }

  return <div className="wallet-setup">…</div>
}
