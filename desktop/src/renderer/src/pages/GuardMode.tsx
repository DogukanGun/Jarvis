import { useCallback, useEffect, useRef, useState } from 'react'
import { verify as verifyBiometric } from '../lib/biometricAuth'
import { useCamera } from '../hooks/useCamera'
import { useWebSocket } from '../hooks/useWebSocket'

type GuardStatus = 'watching' | 'pin-entry' | 'verifying' | 'verified' | 'alert'

const windowApi = (window as unknown as { api?: {
  minimizeWindow?: () => void
  restoreWindow?: () => void
  activateGuard?: () => void
  deactivateGuard?: () => void
  relockGuard?: () => void
  showPinEntry?: () => void
  onGuardCombo?: (cb: () => void) => () => void
  onGuardAlarm?: (cb: () => void) => () => void
} }).api

const PIN_KEY = 'jarvis_guard_pin'

const STATUS_LABEL: Record<GuardStatus, string> = {
  watching: 'watching',
  'pin-entry': 'enter PIN',
  verifying: 'verifying identity',
  verified: 'identity confirmed',
  alert: 'INTRUDER DETECTED',
}

let _alarmCtx: AudioContext | null = null

function playAlarm(): void {
  stopAlarm()
  const ctx = new AudioContext()
  _alarmCtx = ctx
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
  osc.onended = () => { ctx.close(); if (_alarmCtx === ctx) _alarmCtx = null }
}

function stopAlarm(): void {
  if (_alarmCtx) {
    _alarmCtx.close().catch(() => {})
    _alarmCtx = null
  }
}

export default function GuardMode({
  onDeactivate,
}: {
  onDeactivate: () => void
}): React.JSX.Element {
  const [guardStatus, setGuardStatus] = useState<GuardStatus>('watching')
  const [intruderPhoto, setIntruderPhoto] = useState<string | null>(null)
  const [intruderVideoUrl, setIntruderVideoUrl] = useState<string | null>(null)
  const [isAlarming, setIsAlarming] = useState(false)
  const [resetKey, setResetKey] = useState(0)
  const [pinInput, setPinInput] = useState('')
  const [pinError, setPinError] = useState('')
  const [pendingFrame, setPendingFrame] = useState<string | null>(null)

  const { videoRef, ready, capture, startRecording, stopRecording } = useCamera()
  const loopCancelRef = useRef(false)

  // Remote alarm from WebSocket (e.g. another device)
  const onAlarm = useCallback(() => {
    setIsAlarming(true)
    playAlarm()
    setTimeout(() => setIsAlarming(false), 10_000)
  }, [])

  useWebSocket({ onAlarm })

  // Alarm from overlay (mouse move / click / timeout) → record video + go to PIN entry
  useEffect(() => {
    if (guardStatus !== 'watching') return
    const cleanup = windowApi?.onGuardAlarm?.(() => {
      const frame = capture() ?? pendingFrame
      playAlarm()
      setIsAlarming(true)
      setTimeout(() => setIsAlarming(false), 10_000)
      setPendingFrame(frame)
      startRecording()  // start capturing the intruder
      if (frame) {
        fetch('http://localhost:8888/api/security/alert', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            image_b64: frame,
            message: `Motion detected at ${new Date().toLocaleString()}`,
          }),
        }).catch(() => {})
      }
      setGuardStatus('pin-entry')
      setPinInput('')
      setPinError('')
    })
    return () => cleanup?.()
  }, [guardStatus]) // eslint-disable-line react-hooks/exhaustive-deps

  // Activate overlay on mount
  useEffect(() => {
    windowApi?.activateGuard?.()
  }, [])

  // YOLO detection loop
  useEffect(() => {
    if (!ready) return
    if (guardStatus !== 'watching') return

    loopCancelRef.current = false
    let timeoutId: ReturnType<typeof setTimeout>

    async function loop(): Promise<void> {
      if (loopCancelRef.current) return
      const frame = capture()
      if (!frame) { timeoutId = setTimeout(loop, 3000); return }
      try {
        const res = await fetch('http://localhost:8500/api/detect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_b64: frame, confidence_threshold: 0.5 }),
        })
        const data = (await res.json()) as { objects?: { label: string }[] }
        if (data.objects?.some((o) => o.label === 'person')) {
          setPendingFrame(frame)
        }
      } catch { /* vision unavailable */ }
      if (!loopCancelRef.current) timeoutId = setTimeout(loop, 3000)
    }

    timeoutId = setTimeout(loop, 500)
    return () => { loopCancelRef.current = true; clearTimeout(timeoutId) }
  }, [ready, resetKey, guardStatus]) // eslint-disable-line react-hooks/exhaustive-deps

  // X key from overlay → PIN entry (owner intentionally unlocking)
  useEffect(() => {
    if (guardStatus !== 'watching') return
    const cleanup = windowApi?.onGuardCombo?.(() => {
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
      setPinInput('')
      return
    }
    setPinError('')
    setGuardStatus('verifying')
    runBiometricVerification()
  }

  const runBiometricVerification = async () => {
    try {
      const ok = await verifyBiometric()
      if (ok) {
        stopAlarm()
        setIsAlarming(false)
        // Stop recording and store the clip — show it in the verified screen
        const videoUrl = await stopRecording()
        if (videoUrl) setIntruderVideoUrl(videoUrl)
        setGuardStatus('verified')
        // No auto-dismiss — owner watches the clip then clicks Return to Chat
      } else {
        // Biometric failed — capture intruder photo and lock into alert
        const frame = capture() ?? pendingFrame
        setIntruderPhoto(frame)
        setGuardStatus('alert')
        playAlarm()
        setIsAlarming(true)
        setTimeout(() => setIsAlarming(false), 10_000)
        if (frame) {
          fetch('http://localhost:8888/api/security/alert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              image_b64: frame,
              message: `Biometric verification failed at ${new Date().toLocaleString()}`,
            }),
          }).catch(() => {})
        }
      }
    } catch {
      // Biometric unavailable — fall back to PIN-only, stay on pin-entry
      setGuardStatus('pin-entry')
      setPinError('')
    }
  }

  function handleDeactivate(): void {
    windowApi?.deactivateGuard?.()
    onDeactivate()
  }

  return (
    <div className="guard-page">
      <div className="guard-status-bar">
        <span className={`guard-status-indicator ${guardStatus}`}>
          {STATUS_LABEL[guardStatus]}
        </span>
        {/* Only show Return to Chat when actively watching (owner's escape) */}
        {guardStatus === 'watching' && (
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

      {/* PIN Entry — shown for both owner (X key) and intruder (alarm triggered) */}
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

      {/* Verified — show recorded intruder clip then let owner return to chat */}
      {guardStatus === 'verified' && (
        <div className="guard-alert-panel">
          <p className="guard-alert-title" style={{ color: '#4ade80' }}>IDENTITY CONFIRMED</p>
          {intruderVideoUrl ? (
            // eslint-disable-next-line jsx-a11y/media-has-caption
            <video
              src={intruderVideoUrl}
              className="guard-intruder-photo"
              controls
              autoPlay
              loop
            />
          ) : intruderPhoto ? (
            <img
              src={`data:image/jpeg;base64,${intruderPhoto}`}
              className="guard-intruder-photo"
              alt="Intruder snapshot"
            />
          ) : null}
          <button className="guard-activate-btn" onClick={handleDeactivate}>
            Return to Chat
          </button>
        </div>
      )}

      {/* Alert — shown only after biometric failure. Dead end: no reset button. */}
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
        </div>
      )}
    </div>
  )
}
