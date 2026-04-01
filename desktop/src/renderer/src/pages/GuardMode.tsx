import { useCallback, useEffect, useRef, useState } from 'react'
import { verifyAdmin } from '../lib/faceApi'
import { useCamera } from '../hooks/useCamera'
import { useWebSocket } from '../hooks/useWebSocket'

type GuardStatus = 'watching' | 'pin-entry' | 'verifying' | 'verified' | 'alert'

const PIN_KEY = 'jarvis_guard_pin'

const STATUS_LABEL: Record<GuardStatus, string> = {
  watching: 'watching',
  'pin-entry': 'enter PIN',
  verifying: 'verifying face',
  verified: 'identity confirmed',
  alert: 'INTRUDER DETECTED',
}

const windowApi = (window as unknown as { api?: {
  minimizeWindow?: () => void
  restoreWindow?: () => void
  activateGuard?: () => void
  deactivateGuard?: () => void
  showPinEntry?: () => void
  onGuardCombo?: (cb: () => void) => () => void
} }).api

function playAlarm(): void {
  const ctx = new AudioContext()
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.connect(gain)
  gain.connect(ctx.destination)
  osc.type = 'sawtooth'
  gain.gain.setValueAtTime(1.0, ctx.currentTime)

  let t = ctx.currentTime
  for (let i = 0; i < 20; i++) {
    osc.frequency.setValueAtTime(i % 2 === 0 ? 880 : 440, t)
    t += 0.5
  }
  osc.start(ctx.currentTime)
  osc.stop(ctx.currentTime + 10)
  osc.onended = () => ctx.close()
}

export default function GuardMode({
  onDeactivate,
}: {
  onDeactivate: () => void
}): React.JSX.Element {
  const [guardStatus, setGuardStatus] = useState<GuardStatus>('watching')
  const [intruderPhoto, setIntruderPhoto] = useState<string | null>(null)
  const [isAlarming, setIsAlarming] = useState(false)
  const [resetKey, setResetKey] = useState(0)
  const [pinInput, setPinInput] = useState('')
  const [pinError, setPinError] = useState('')
  const [pendingFrame, setPendingFrame] = useState<string | null>(null)
  const [countdown, setCountdown] = useState(0)
  const personDetectedRef = useRef(false)

  const { videoRef, ready, capture } = useCamera()
  const loopCancelRef = useRef(false)

  const onAlarm = useCallback(() => {
    setIsAlarming(true)
    playAlarm()
    setTimeout(() => setIsAlarming(false), 10_000)
  }, [])

  useWebSocket({ onAlarm })

  // Activate overlay + minimize on mount
  useEffect(() => {
    windowApi?.activateGuard?.()
  }, [])

  // YOLO detection loop — tracks if a person is present, does NOT show PIN
  useEffect(() => {
    if (!ready) return
    if (guardStatus !== 'watching') return

    loopCancelRef.current = false
    let timeoutId: ReturnType<typeof setTimeout>

    async function loop(): Promise<void> {
      if (loopCancelRef.current) return

      const frame = capture()
      if (!frame) {
        timeoutId = setTimeout(loop, 3000)
        return
      }

      try {
        const res = await fetch('http://localhost:8500/api/detect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_b64: frame, confidence_threshold: 0.5 }),
        })
        const data = (await res.json()) as { objects?: { label: string }[] }
        personDetectedRef.current = data.objects?.some((o) => o.label === 'person') ?? false
        if (personDetectedRef.current) {
          setPendingFrame(frame)
        }
      } catch {
        // Vision service unavailable
      }

      if (!loopCancelRef.current) {
        timeoutId = setTimeout(loop, 3000)
      }
    }

    timeoutId = setTimeout(loop, 500)

    return () => {
      loopCancelRef.current = true
      clearTimeout(timeoutId)
    }
  }, [ready, resetKey, guardStatus]) // eslint-disable-line react-hooks/exhaustive-deps

  // Listen for unlock combo (Shift Shift Enter Enter) from overlay
  useEffect(() => {
    if (guardStatus !== 'watching') return

    const cleanup = windowApi?.onGuardCombo?.(() => {
      // Combo entered — show PIN entry
      setGuardStatus('pin-entry')
      setPinInput('')
      setPinError('')
    })

    return () => cleanup?.()
  }, [guardStatus])

  const handlePinSubmit = () => {
    const savedPin = localStorage.getItem(PIN_KEY)
    if (pinInput !== savedPin) {
      setPinError('Wrong PIN')
      return
    }

    // Correct PIN — give 4 seconds for face positioning
    setPinError('')
    setGuardStatus('verifying')
    setCountdown(4)

    let c = 4
    const countdownInterval = setInterval(() => {
      c--
      setCountdown(c)
      if (c <= 0) {
        clearInterval(countdownInterval)
        runFaceVerification()
      }
    }, 1000)
  }

  const runFaceVerification = async () => {
    const frame = capture() ?? pendingFrame
    if (!frame) {
      setGuardStatus('alert')
      setIntruderPhoto(null)
      triggerAlarm(null)
      return
    }

    try {
      const result = await verifyAdmin(frame)

      if (result.success && result.data === true) {
        // Admin verified — deactivate guard, go to chat
        setGuardStatus('verified')
        setTimeout(() => {
          windowApi?.deactivateGuard?.()
          onDeactivate()
        }, 1000)
      } else {
        // Face doesn't match — intruder
        setGuardStatus('alert')
        setIntruderPhoto(frame)
        triggerAlarm(frame)
      }
    } catch {
      // Face service error — retry
      setGuardStatus('watching')
      windowApi?.minimizeWindow?.()
    }
  }

  function triggerAlarm(frame: string | null): void {
    playAlarm()
    setIsAlarming(true)
    setTimeout(() => setIsAlarming(false), 10_000)

    if (frame) {
      fetch('http://localhost:8888/api/security/alert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_b64: frame,
          message: `Intruder detected at ${new Date().toLocaleString()}`,
        }),
      }).catch(() => {})
    }
  }

  function handleReset(): void {
    setGuardStatus('watching')
    setIntruderPhoto(null)
    setIsAlarming(false)
    setPinInput('')
    setPinError('')
    setPendingFrame(null)
    setResetKey((k) => k + 1)
    windowApi?.activateGuard?.()
  }

  function handleDeactivate(): void {
    windowApi?.deactivateGuard?.()
    onDeactivate()
  }

  return (
    <div className="guard-page">
      <div className="guard-status-bar">
        <span className={`guard-status-indicator ${guardStatus}`}>
          {guardStatus === 'verifying' && countdown > 0
            ? `look at camera... ${countdown}`
            : STATUS_LABEL[guardStatus]}
        </span>
        {guardStatus !== 'alert' && (
          <button className="guard-deactivate-btn" onClick={handleDeactivate}>
            Return to Chat
          </button>
        )}
      </div>

      <div className="guard-camera-container">
        {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
        <video ref={videoRef} autoPlay playsInline muted className="camera-feed" />
        {guardStatus === 'verifying' && <div className="scan-overlay" />}
        {isAlarming && <div className="alarm-overlay" />}
      </div>

      {/* PIN Entry Panel */}
      {guardStatus === 'pin-entry' && (
        <div className="guard-pin-panel">
          <p className="guard-pin-title">ENTER PIN</p>
          <input
            className="guard-pin-field"
            type="password"
            inputMode="numeric"
            value={pinInput}
            onChange={(e) => { setPinInput(e.target.value); setPinError('') }}
            onKeyDown={(e) => e.key === 'Enter' && handlePinSubmit()}
            autoFocus
          />
          {pinError && <p className="guard-pin-error">{pinError}</p>}
          <button className="guard-pin-submit" onClick={handlePinSubmit}>
            Verify
          </button>
        </div>
      )}

      {/* Alert Panel */}
      {guardStatus === 'alert' && (
        <div className="guard-alert-panel">
          <p className="guard-alert-title">INTRUDER DETECTED</p>
          {intruderPhoto && (
            <img
              src={`data:image/jpeg;base64,${intruderPhoto}`}
              className="guard-intruder-photo"
              alt="Intruder"
            />
          )}
          <button className="guard-reset-btn" onClick={handleReset}>
            Reset Watch
          </button>
        </div>
      )}
    </div>
  )
}
