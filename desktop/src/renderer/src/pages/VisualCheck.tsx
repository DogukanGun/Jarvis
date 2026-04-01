import { useEffect, useRef, useState } from 'react'
import { adminExists, enrollAdmin, verifyAdmin, deleteAdmin } from '../lib/faceApi'
import { useCamera } from '../hooks/useCamera'

type State =
  | 'checking'
  | 'no_admin'
  | 'enrolling'
  | 'enrolled'
  | 'verifying'
  | 'verified'
  | 'denied'
  | 'error'

export default function VisualCheck({ onVerified }: { onVerified?: () => void }): React.JSX.Element {
  const [state, setState] = useState<State>('checking')
  const [statusMsg, setStatusMsg] = useState('Initializing…')
  const loopRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [showReset, setShowReset] = useState(false)
  const [resetPassword, setResetPassword] = useState('')
  const [resetError, setResetError] = useState('')
  const [resetting, setResetting] = useState(false)

  const { videoRef, ready, error: camError, capture, stop } = useCamera()

  // Step 1: check if admin exists on mount
  useEffect(() => {
    adminExists()
      .then((exists) => {
        if (exists) {
          setState('verifying')
          setStatusMsg('Please look at the camera to verify your identity.')
        } else {
          setState('no_admin')
          setStatusMsg('No admin registered. Please look at the camera.')
        }
      })
      .catch(() => {
        setState('error')
        setStatusMsg('Could not reach the Face API. Make sure it is running on port 8400.')
      })
  }, [])

  // Step 2a: transition no_admin → enrolling (separate effect to avoid self-cancel)
  useEffect(() => {
    if (state !== 'no_admin' || !ready) return
    setState('enrolling')
  }, [state, ready])

  // Step 2b: enrollment loop — only runs when state is already 'enrolling'
  // Keeping state stable inside the loop means setState('verified') won't be
  // swallowed by the effect cleanup cancelling mid-flight.
  useEffect(() => {
    if (state !== 'enrolling' || !ready) return

    let cancelled = false

    async function tryEnroll(): Promise<void> {
      if (cancelled) return
      setStatusMsg('Looking for your face…')

      const img = capture()
      if (!img) {
        loopRef.current = setTimeout(tryEnroll, 1500)
        return
      }

      const result = await enrollAdmin(img).catch(() => ({ error: 'network error' }))

      if (cancelled) return

      if ('success' in result && result.success) {
        stop()
        setStatusMsg('Admin registered. Welcome!')
        setState('verified')
      } else {
        loopRef.current = setTimeout(tryEnroll, 1500)
      }
    }

    loopRef.current = setTimeout(tryEnroll, 1000)

    return () => {
      cancelled = true
      if (loopRef.current) clearTimeout(loopRef.current)
    }
  }, [state, ready])

  // Step 3: verification loop
  useEffect(() => {
    if (state !== 'verifying' || !ready) return

    let cancelled = false

    async function tryVerify(): Promise<void> {
      if (cancelled) return
      setStatusMsg('Verifying your identity…')

      const img = capture()
      if (!img) {
        loopRef.current = setTimeout(tryVerify, 1500)
        return
      }

      const result = await verifyAdmin(img).catch(() => ({ error: 'network error' }))

      if (cancelled) return

      if ('success' in result && result.success && result.data === true) {
        stop()
        setState('verified')
        setStatusMsg('Identity verified. Welcome back!')
      } else {
        // face not recognised or not detected — retry
        setStatusMsg('Face not recognised. Retrying...')
        loopRef.current = setTimeout(tryVerify, 1500)
      }
    }

    loopRef.current = setTimeout(tryVerify, 1000)

    return () => {
      cancelled = true
      if (loopRef.current) clearTimeout(loopRef.current)
    }
  }, [state, ready])

  useEffect(() => {
    if (state === 'verified' && onVerified) {
      const timer = setTimeout(onVerified, 1500)
      return () => clearTimeout(timer)
    }
    return undefined
  }, [state, onVerified])

  const showCamera = ['no_admin', 'enrolling', 'verifying'].includes(state)
  // 'no_admin' is a transient state (<1 render) before 'enrolling' kicks in

  async function handleReset(): Promise<void> {
    if (!resetPassword) return
    setResetting(true)
    setResetError('')
    try {
      const ok = await (window as any).api.verifyAdminPassword(resetPassword)
      if (!ok) {
        setResetError('Wrong password.')
        setResetting(false)
        return
      }
      await deleteAdmin()
      setShowReset(false)
      setResetPassword('')
      setState('checking')
      setStatusMsg('Initializing…')
      // Re-run the admin exists check
      adminExists()
        .then((exists) => {
          if (exists) {
            setState('verifying')
            setStatusMsg('Please look at the camera to verify your identity.')
          } else {
            setState('no_admin')
            setStatusMsg('No admin registered. Please look at the camera.')
          }
        })
        .catch(() => setState('error'))
    } catch {
      setResetError('Reset failed. Try again.')
      setResetting(false)
    }
  }

  return (
    <div className="visual-check">
      {/* Status message */}
      <p
        className={`status-text ${
          state === 'verified' || state === 'enrolled'
            ? 'success'
            : state === 'error' || state === 'denied'
              ? 'error'
              : ''
        }`}
      >
        {camError ?? statusMsg}
      </p>

      {/* Camera feed */}
      <div className={`camera-container ${showCamera ? 'visible' : 'hidden'}`}>
        {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
        <video ref={videoRef} autoPlay playsInline muted className="camera-feed" />
        {(state === 'enrolling' || state === 'verifying') && <div className="scan-overlay" />}
      </div>

      {/* Result icons */}
      {state === 'verified' && <div className="enrolled-icon">✓</div>}
      {state === 'denied' && <div className="enrolled-icon error">✗</div>}

      {/* Reset enrollment — only shown during verification */}
      {state === 'verifying' && !showReset && (
        <button
          className="reset-link"
          onClick={() => { setShowReset(true); setResetError('') }}
        >
          Reset enrollment
        </button>
      )}

      {showReset && (
        <div className="reset-modal">
          <p className="reset-label">Enter admin password to reset face enrollment</p>
          <input
            type="password"
            className="reset-input"
            placeholder="Password"
            value={resetPassword}
            onChange={(e) => setResetPassword(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleReset() }}
            autoFocus
          />
          {resetError && <p className="reset-error">{resetError}</p>}
          <div className="reset-actions">
            <button className="reset-confirm" onClick={handleReset} disabled={resetting}>
              {resetting ? 'Verifying…' : 'Confirm Reset'}
            </button>
            <button className="reset-cancel" onClick={() => { setShowReset(false); setResetPassword(''); setResetError('') }}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
