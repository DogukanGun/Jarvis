import { useEffect, useState } from 'react'
import { isBiometricAvailable, verify } from '../lib/biometricAuth'

type State = 'checking' | 'verifying' | 'verified' | 'unavailable' | 'error'

export default function VisualCheck({ onVerified }: { onVerified?: () => void }): React.JSX.Element {
  const [state, setState] = useState<State>('checking')
  const [statusMsg, setStatusMsg] = useState('Initializing…')

  useEffect(() => {
    let cancelled = false

    async function run(): Promise<void> {
      const available = await isBiometricAvailable()

      if (!available) {
        if (!cancelled) {
          setState('unavailable')
          setStatusMsg('Biometric authentication is not available on this device. Proceeding…')
          setTimeout(() => onVerified?.(), 1500)
        }
        return
      }

      if (cancelled) return
      setState('verifying')
      setStatusMsg('Verify your identity…')

      try {
        const ok = await verify()
        if (cancelled) return

        if (ok) {
          setState('verified')
          setStatusMsg('Identity verified. Welcome back!')
        } else {
          setState('error')
          setStatusMsg('Verification cancelled or failed. Please try again.')
        }
      } catch {
        if (!cancelled) {
          setState('error')
          setStatusMsg('Verification failed. Please try again.')
        }
      }
    }

    run()
    return () => { cancelled = true }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (state === 'verified' && onVerified) {
      const timer = setTimeout(onVerified, 1500)
      return () => clearTimeout(timer)
    }
  }, [state, onVerified])

  const retry = async (): Promise<void> => {
    setState('verifying')
    setStatusMsg('Verify your identity…')
    try {
      const ok = await verify()
      if (ok) {
        setState('verified')
        setStatusMsg('Identity verified. Welcome back!')
      } else {
        setState('error')
        setStatusMsg('Verification cancelled. Please try again.')
      }
    } catch {
      setState('error')
      setStatusMsg('Verification failed. Please try again.')
    }
  }

  return (
    <div className="visual-check">
      <p
        className={`status-text ${
          state === 'verified'
            ? 'success'
            : state === 'error'
              ? 'error'
              : ''
        }`}
      >
        {statusMsg}
      </p>

      {(state === 'checking' || state === 'verifying') && (
        <div className="biometric-icon">
          <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 10v4" />
            <path d="M7.5 8a5.5 5.5 0 0 1 9 0" />
            <path d="M5 6a9 9 0 0 1 14 0" />
            <path d="M7.5 16a5.5 5.5 0 0 0 9 0" />
            <path d="M5 18a9 9 0 0 0 14 0" />
            <circle cx="12" cy="12" r="1" />
          </svg>
        </div>
      )}

      {state === 'verified' && <div className="enrolled-icon">&#x2713;</div>}

      {state === 'error' && (
        <>
          <div className="enrolled-icon error">&#x2717;</div>
          <button className="retry-btn" onClick={retry}>Retry</button>
        </>
      )}
    </div>
  )
}
