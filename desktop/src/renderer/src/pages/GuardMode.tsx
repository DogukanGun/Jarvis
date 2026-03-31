import { useCallback, useEffect, useRef, useState } from 'react'
import { verifyAdmin } from '../lib/faceApi'
import { useCamera } from '../hooks/useCamera'
import { useWebSocket } from '../hooks/useWebSocket'

type GuardStatus = 'watching' | 'verifying' | 'verified' | 'alert'

const STATUS_LABEL: Record<GuardStatus, string> = {
  watching: 'watching',
  verifying: 'verifying...',
  verified: 'identity confirmed',
  alert: 'INTRUDER DETECTED',
}

function playAlarm(): void {
  const ctx = new AudioContext()
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.connect(gain)
  gain.connect(ctx.destination)
  osc.type = 'sawtooth'
  gain.gain.setValueAtTime(1.0, ctx.currentTime)

  // Alternate 880 Hz / 440 Hz every 0.5 s for 10 s
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
  const [resetKey, setResetKey] = useState(0) // increment to restart the detection loop

  const { videoRef, ready, capture } = useCamera()
  const loopCancelRef = useRef(false)

  // Alarm triggered remotely via /trigger
  const onAlarm = useCallback(() => {
    setIsAlarming(true)
    playAlarm()
    setTimeout(() => setIsAlarming(false), 10_000)
  }, [])

  useWebSocket({ onAlarm })

  // Detection loop
  useEffect(() => {
    if (!ready) return

    loopCancelRef.current = false
    let timeoutId: ReturnType<typeof setTimeout>

    async function loop(): Promise<void> {
      if (loopCancelRef.current) return

      const frame = capture()
      if (!frame) {
        timeoutId = setTimeout(loop, 3000)
        return
      }

      // 1. YOLO detection
      let personFound = false
      try {
        const res = await fetch('http://localhost:8500/api/detect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_b64: frame, confidence_threshold: 0.5 }),
        })
        const data = (await res.json()) as { objects?: { label: string }[] }
        personFound = data.objects?.some((o) => o.label === 'person') ?? false
      } catch {
        // Vision service unavailable — keep watching silently
      }

      if (loopCancelRef.current) return

      if (!personFound) {
        setGuardStatus('watching')
        timeoutId = setTimeout(loop, 3000)
        return
      }

      // 2. Person detected — run face verification
      setGuardStatus('verifying')
      try {
        const verifyResult = await verifyAdmin(frame)

        if (loopCancelRef.current) return

        if (verifyResult.success && verifyResult.data === true) {
          // Admin confirmed — briefly show and reset
          setGuardStatus('verified')
          timeoutId = setTimeout(() => {
            if (!loopCancelRef.current) {
              setGuardStatus('watching')
              loop()
            }
          }, 2000)
          return
        }

        // 3. Intruder — halt loop, alert user
        setGuardStatus('alert')
        setIntruderPhoto(frame)

        try {
          await fetch('http://localhost:8888/api/security/alert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              image_b64: frame,
              message: `Intruder detected at ${new Date().toLocaleString()}`,
            }),
          })
        } catch {
          // Router unavailable — alert still shown locally
        }
        // Loop halts here — user must click Reset Watch
      } catch {
        // Face service unavailable — retry
        timeoutId = setTimeout(loop, 3000)
      }
    }

    timeoutId = setTimeout(loop, 500)

    return () => {
      loopCancelRef.current = true
      clearTimeout(timeoutId)
    }
  }, [ready, resetKey]) // eslint-disable-line react-hooks/exhaustive-deps

  function handleReset(): void {
    setGuardStatus('watching')
    setIntruderPhoto(null)
    setResetKey((k) => k + 1)
  }

  return (
    <div className="guard-page">
      <div className="guard-status-bar">
        <span className={`guard-status-indicator ${guardStatus}`}>
          {STATUS_LABEL[guardStatus]}
        </span>
        <button className="guard-deactivate-btn" onClick={onDeactivate}>
          Return to Chat
        </button>
      </div>

      <div className="guard-camera-container">
        {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
        <video ref={videoRef} autoPlay playsInline muted className="camera-feed" />
        {guardStatus === 'verifying' && <div className="scan-overlay" />}
        {isAlarming && <div className="alarm-overlay" />}
      </div>

      {guardStatus === 'alert' && intruderPhoto && (
        <div className="guard-alert-panel">
          <p className="guard-alert-title">INTRUDER DETECTED</p>
          {/* Mirror the image so it matches what the camera captured */}
          <img
            src={`data:image/jpeg;base64,${intruderPhoto}`}
            className="guard-intruder-photo"
            alt="Intruder"
          />
          <button className="guard-reset-btn" onClick={handleReset}>
            Reset Watch
          </button>
        </div>
      )}
    </div>
  )
}
