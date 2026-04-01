import { useEffect, useRef, useState } from 'react'
import { adminExists, enrollAdmin, verifyAdmin } from '../lib/faceApi'
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

  // Step 2: enroll loop when no admin
  useEffect(() => {
    if (state !== 'no_admin' || !ready) return

    let cancelled = false

    async function tryEnroll(): Promise<void> {
      if (cancelled) return
      setState('enrolling')
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
        setState('verified')
        setStatusMsg('Admin registered. Welcome!')
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

      if (result.success && result.data === true) {
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
  }, [state, onVerified])

  const showCamera = ['no_admin', 'enrolling', 'verifying'].includes(state)

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
    </div>
  )
}
