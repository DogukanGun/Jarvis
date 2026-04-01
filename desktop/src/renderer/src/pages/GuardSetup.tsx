import { useState, useEffect } from 'react'

const PIN_KEY = 'jarvis_guard_pin'

export default function GuardSetup({
  onActivate,
  onCancel,
}: {
  onActivate: (options: { lockKeyboard: boolean; lockMouse: boolean; voiceAlert: boolean }) => void
  onCancel: () => void
}): React.JSX.Element {
  const [pin, setPin] = useState('')
  const [confirmPin, setConfirmPin] = useState('')
  const [hasExistingPin, setHasExistingPin] = useState(false)
  const [lockKeyboard, setLockKeyboard] = useState(true)
  const [lockMouse, setLockMouse] = useState(true)
  const [voiceAlert, setVoiceAlert] = useState(true)
  const [error, setError] = useState('')
  const [mode, setMode] = useState<'check' | 'create' | 'confirm'>('check')

  useEffect(() => {
    const saved = localStorage.getItem(PIN_KEY)
    if (saved) {
      setHasExistingPin(true)
      setMode('confirm')
    } else {
      setMode('create')
    }
  }, [])

  const handleCreate = () => {
    if (pin.length < 4) {
      setError('PIN must be at least 4 digits')
      return
    }
    if (!/^\d+$/.test(pin)) {
      setError('PIN must be numbers only')
      return
    }
    if (pin !== confirmPin) {
      setError('PINs do not match')
      return
    }
    localStorage.setItem(PIN_KEY, pin)
    setError('')
    onActivate({ lockKeyboard, lockMouse, voiceAlert })
  }

  const handleConfirm = () => {
    const saved = localStorage.getItem(PIN_KEY)
    if (pin === saved) {
      setError('')
      onActivate({ lockKeyboard, lockMouse, voiceAlert })
    } else {
      setError('Incorrect PIN')
    }
  }

  return (
    <div className="guard-setup">
      <h2 className="guard-setup-title">Guard Mode</h2>

      {mode === 'create' && (
        <>
          <p className="guard-setup-hint">Create a numeric PIN to lock your machine</p>
          <input
            className="guard-pin-input"
            type="password"
            inputMode="numeric"
            placeholder="Enter PIN"
            value={pin}
            onChange={(e) => { setPin(e.target.value); setError('') }}
            autoFocus
          />
          <input
            className="guard-pin-input"
            type="password"
            inputMode="numeric"
            placeholder="Confirm PIN"
            value={confirmPin}
            onChange={(e) => { setConfirmPin(e.target.value); setError('') }}
          />
        </>
      )}

      {mode === 'confirm' && (
        <>
          <p className="guard-setup-hint">Enter your PIN to activate</p>
          <input
            className="guard-pin-input"
            type="password"
            inputMode="numeric"
            placeholder="Enter PIN"
            value={pin}
            onChange={(e) => { setPin(e.target.value); setError('') }}
            onKeyDown={(e) => e.key === 'Enter' && handleConfirm()}
            autoFocus
          />
        </>
      )}

      {error && <p className="guard-setup-error">{error}</p>}

      <div className="guard-lock-options">
        <label className="guard-lock-option">
          <input
            type="checkbox"
            checked={lockKeyboard}
            onChange={(e) => setLockKeyboard(e.target.checked)}
          />
          <span>Lock Keyboard</span>
        </label>
        <label className="guard-lock-option">
          <input
            type="checkbox"
            checked={lockMouse}
            onChange={(e) => setLockMouse(e.target.checked)}
          />
          <span>Lock Mouse</span>
        </label>
        <label className="guard-lock-option">
          <input
            type="checkbox"
            checked={voiceAlert}
            onChange={(e) => setVoiceAlert(e.target.checked)}
          />
          <span>Voice Alert</span>
        </label>
      </div>

      <div className="guard-setup-actions">
        <button
          className="guard-activate-btn"
          onClick={mode === 'create' ? handleCreate : handleConfirm}
        >
          Activate Guard
        </button>
        <button className="guard-cancel-btn" onClick={onCancel}>
          Cancel
        </button>
        {hasExistingPin && (
          <button
            className="guard-reset-pin-btn"
            onClick={() => {
              localStorage.removeItem(PIN_KEY)
              setHasExistingPin(false)
              setMode('create')
              setPin('')
              setConfirmPin('')
              setError('')
            }}
          >
            Reset PIN
          </button>
        )}
      </div>
    </div>
  )
}
