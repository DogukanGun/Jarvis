import { useEffect, useRef, useState } from 'react'
import { adminExists, enrollAdmin } from '../lib/faceApi'
import { useCamera } from '../hooks/useCamera'

type State = 'checking' | 'no_admin' | 'enrolling' | 'enrolled' | 'admin_exists' | 'error'

export default function VisualCheck(): React.JSX.Element {
  const [state, setState] = useState<State>('checking')
  const [statusMsg, setStatusMsg] = useState('Initializing…')
  const enrollLoopRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { videoRef, ready, error: camError, capture, stop } = useCamera()

  // Step 1: check if admin exists on mount
  useEffect(() => {
    adminExists()
      .then((exists) => {
        if (exists) {
          setState('admin_exists')
          setStatusMsg('Admin on file — identity verification coming soon.')
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

  // Step 2: once camera is ready and state is no_admin, start auto-enroll loop
  useEffect(() => {
    if (state !== 'no_admin' || !ready) return

    let cancelled = false

    async function tryEnroll(): Promise<void> {
      if (cancelled) return
      setState('enrolling')
      setStatusMsg('Looking for your face…')

      const img = capture()
      if (!img) {
        // camera not ready yet, retry
        enrollLoopRef.current = setTimeout(tryEnroll, 1500)
        return
      }

      const result = await enrollAdmin(img).catch(() => ({ error: 'network error' }))

      if (cancelled) return

      if ('success' in result && result.success) {
        stop()
        setState('enrolled')
        setStatusMsg('Admin registered! Welcome.')
      } else {
        // no face detected — retry silently
        enrollLoopRef.current = setTimeout(tryEnroll, 1500)
      }
    }

    // small delay to let the camera stabilize before first capture
    enrollLoopRef.current = setTimeout(tryEnroll, 1000)

    return () => {
      cancelled = true
      if (enrollLoopRef.current) clearTimeout(enrollLoopRef.current)
    }
  }, [state, ready])

  const showCamera = state === 'no_admin' || state === 'enrolling'

  return (
    <div className="visual-check">
      {/* Status message */}
      <p className={`status-text ${state === 'enrolled' ? 'success' : state === 'error' ? 'error' : ''}`}>
        {camError ?? statusMsg}
      </p>

      {/* Camera feed — visible while enrolling */}
      <div className={`camera-container ${showCamera ? 'visible' : 'hidden'}`}>
        {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
        <video ref={videoRef} autoPlay playsInline muted className="camera-feed" />
        {state === 'enrolling' && <div className="scan-overlay" />}
      </div>

      {/* Enrolled checkmark */}
      {state === 'enrolled' && (
        <div className="enrolled-icon">✓</div>
      )}
    </div>
  )
}
