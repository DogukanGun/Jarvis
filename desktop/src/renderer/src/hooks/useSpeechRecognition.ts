import { useEffect, useRef, useState, useCallback } from 'react'

const TRANSCRIBE_URL = 'http://localhost:8888/api/transcribe'

type MicState = 'idle' | 'recording' | 'transcribing'

export function useSpeechRecognition(onResult: (transcript: string) => void) {
  const [micState, setMicState] = useState<MicState>('idle')
  const [supported, setSupported] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const onResultRef = useRef(onResult)

  useEffect(() => {
    onResultRef.current = onResult
  }, [onResult])

  useEffect(() => {
    setSupported(!!navigator.mediaDevices?.getUserMedia)
  }, [])

  const startListening = useCallback(async () => {
    if (micState !== 'idle') return

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm'
      })

      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        streamRef.current = null

        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        chunksRef.current = []

        if (blob.size < 1000) {
          setMicState('idle')
          return
        }

        setMicState('transcribing')

        try {
          const form = new FormData()
          form.append('file', blob, 'recording.webm')
          const resp = await fetch(TRANSCRIBE_URL, { method: 'POST', body: form })
          const data = await resp.json()
          const text = (data.text || '').trim()
          if (text) {
            onResultRef.current(text)
          }
        } catch (err) {
          console.error('Transcription failed:', err)
        }

        setMicState('idle')
      }

      mediaRecorderRef.current = mediaRecorder
      mediaRecorder.start()
      setMicState('recording')
    } catch (err) {
      console.error('Microphone access failed:', err)
      setMicState('idle')
    }
  }, [micState])

  const stopListening = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
      mediaRecorderRef.current = null
    }
  }, [])

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop()
      }
      streamRef.current?.getTracks().forEach((t) => t.stop())
    }
  }, [])

  return {
    micState,
    listening: micState === 'recording',
    supported,
    startListening,
    stopListening
  }
}
