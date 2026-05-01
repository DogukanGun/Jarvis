import { useCallback, useEffect, useRef, useState } from 'react'

export function useCamera() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [ready, setReady] = useState(false)
  const [active, setActive] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const startCamera = useCallback(async () => {
    if (streamRef.current) return // already running
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user' },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.onloadedmetadata = () => {
          setReady(true)
          setActive(true)
          setError(null)
        }
      }
    } catch (err: unknown) {
      setError(`Camera error: ${(err as Error).message}`)
    }
  }, [])

  const stopCamera = useCallback(() => {
    recorderRef.current?.stop()
    recorderRef.current = null
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setReady(false)
    setActive(false)
  }, [])

  // Start on mount
  useEffect(() => {
    startCamera()
    return () => {
      recorderRef.current?.stop()
      streamRef.current?.getTracks().forEach((t) => t.stop())
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function capture(): string | null {
    const video = videoRef.current
    if (!video || !ready) return null
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d')!.drawImage(video, 0, 0)
    return canvas.toDataURL('image/jpeg', 0.85).split(',')[1]
  }

  function startRecording(): void {
    if (!streamRef.current || recorderRef.current) return
    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
      ? 'video/webm;codecs=vp9'
      : MediaRecorder.isTypeSupported('video/webm')
        ? 'video/webm'
        : ''
    chunksRef.current = []
    const recorder = new MediaRecorder(streamRef.current, mimeType ? { mimeType } : undefined)
    recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
    recorder.start(200)
    recorderRef.current = recorder
  }

  function stopRecording(): Promise<string | null> {
    return new Promise((resolve) => {
      const recorder = recorderRef.current
      if (!recorder) { resolve(null); return }
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'video/webm' })
        resolve(URL.createObjectURL(blob))
        recorderRef.current = null
        chunksRef.current = []
      }
      recorder.stop()
    })
  }

  function stop(): void {
    stopCamera()
  }

  return { videoRef, ready, active, error, capture, startCamera, stopCamera, startRecording, stopRecording, stop }
}
