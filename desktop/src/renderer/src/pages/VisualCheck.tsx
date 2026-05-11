import { useEffect, useState } from 'react'
import { isBiometricAvailable, verify } from '../lib/biometricAuth'
import jarvisLogo from '../assets/jarvis-logo.svg'

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
    return undefined
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
      <img src={jarvisLogo} alt="Jarvis" className="welcome-logo" />
      <h1 className="welcome-title">JARVIS</h1>
      <p className="welcome-tagline">Your AI Agent</p>
      <div className="welcome-divider" />
      <div className="welcome-status">
        <span className={`status-dot ${state}`} />
        <p className={`status-text${state === 'verified' ? ' success' : state === 'error' ? ' error' : ''}`}>
          {statusMsg}
        </p>
      </div>
      {state === 'error' && (
        <button className="retry-btn" onClick={retry}>Retry</button>
      )}
    </div>
  )
}
