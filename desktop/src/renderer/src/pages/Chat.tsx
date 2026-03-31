import { useState, useEffect, useRef, useCallback } from 'react'
import { useWebSocket, WsResponse } from '../hooks/useWebSocket'
import { useSpeechRecognition } from '../hooks/useSpeechRecognition'
import { useCamera } from '../hooks/useCamera'

type Message = {
  id: string
  role: 'user' | 'assistant' | 'status'
  content: string
  displayedContent: string
  isTyping: boolean
  timestamp: number
}

export default function Chat({
  userId = 'admin',
  onGuardMode,
}: {
  userId?: string
  onGuardMode?: () => void
}): React.JSX.Element {
  const [messages, setMessages] = useState<Message[]>([])
  const [waiting, setWaiting] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const onStatus = useCallback((text: string) => {
    setMessages((prev) => {
      const lastStatusIdx = prev.findLastIndex((m) => m.role === 'status')
      if (lastStatusIdx !== -1) {
        const updated = [...prev]
        updated[lastStatusIdx] = {
          ...updated[lastStatusIdx],
          content: text,
          displayedContent: text
        }
        return updated
      }
      return [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'status',
          content: text,
          displayedContent: text,
          isTyping: false,
          timestamp: Date.now()
        }
      ]
    })
  }, [])

  const onResponse = useCallback((data: WsResponse) => {
    setWaiting(false)
    setMessages((prev) => {
      // Remove last status message
      const filtered = prev.filter((m, i) => {
        if (m.role === 'status' && i === prev.findLastIndex((p) => p.role === 'status')) {
          return false
        }
        return true
      })
      // Finish any still-typing messages instantly
      const finalized = filtered.map((m) =>
        m.isTyping ? { ...m, displayedContent: m.content, isTyping: false } : m
      )
      return [
        ...finalized,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.content,
          displayedContent: '',
          isTyping: true,
          timestamp: Date.now()
        }
      ]
    })
  }, [])

  const onError = useCallback((text: string) => {
    setWaiting(false)
    setMessages((prev) => {
      const finalized = prev.map((m) =>
        m.isTyping ? { ...m, displayedContent: m.content, isTyping: false } : m
      )
      return [
        ...finalized,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `Error: ${text}`,
          displayedContent: '',
          isTyping: true,
          timestamp: Date.now()
        }
      ]
    })
  }, [])

  const { status, send } = useWebSocket({ onStatus, onResponse, onError })
  const { videoRef, ready: cameraReady, capture } = useCamera()

  const sendMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || waiting || status !== 'connected') return

      // Capture frame on-demand when sending a message
      const frame = cameraReady ? capture() : null

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'user',
          content: trimmed,
          displayedContent: trimmed,
          isTyping: false,
          timestamp: Date.now()
        }
      ])
      setWaiting(true)
      send(userId, trimmed, frame ?? undefined)
    },
    [waiting, status, send, userId, cameraReady, capture]
  )

  const { micState, supported, startListening, stopListening } = useSpeechRecognition(sendMessage)

  // Typing animation — find the LAST message that is still typing
  useEffect(() => {
    const typingIdx = messages.findLastIndex((m) => m.isTyping)
    if (typingIdx === -1) return

    const typingMsg = messages[typingIdx]

    const interval = setInterval(() => {
      setMessages((prev) =>
        prev.map((m) => {
          if (m.id !== typingMsg.id || !m.isTyping) return m
          const nextLen = m.displayedContent.length + 1
          if (nextLen >= m.content.length) {
            return { ...m, displayedContent: m.content, isTyping: false }
          }
          return { ...m, displayedContent: m.content.slice(0, nextLen) }
        })
      )
    }, 20)

    return () => clearInterval(interval)
  }, [messages])

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const micDisabled = !supported || status !== 'connected' || waiting || micState === 'transcribing'

  const micHint =
    micState === 'recording'
      ? 'Listening... click to stop'
      : micState === 'transcribing'
        ? 'Transcribing...'
        : ''

  return (
    <div className="chat-page">
      <div className={`chat-status-bar ${status === 'connected' ? 'connected' : ''}`}>
        <span>
          {status === 'connected'
            ? 'jarvis'
            : status === 'disconnected'
              ? 'disconnected — waiting for router on :8888'
              : 'connecting...'}
        </span>
        {onGuardMode && (
          <button className="guard-mode-btn" onClick={onGuardMode}>
            Guard Mode
          </button>
        )}
      </div>

      <div className="chat-messages">
        {messages.length === 0 && status === 'connected' && micState === 'idle' && (
          <div className="chat-msg status">Press the mic and speak...</div>
        )}
        {messages.length === 0 && status !== 'connected' && (
          <div className="chat-msg status">Waiting for connection to Jarvis router...</div>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-msg ${msg.role}`}>
            {msg.role === 'assistant' || msg.role === 'status'
              ? msg.displayedContent
              : msg.content}
            {msg.isTyping && <span className="chat-cursor">_</span>}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Hidden video element keeps camera warm for on-demand capture */}
      <video ref={videoRef} autoPlay playsInline muted className="camera-hidden" />

      <div className="chat-input-bar">
        {micHint && <span className="mic-hint">{micHint}</span>}
        <button
          className={`mic-button ${micState === 'recording' ? 'active' : ''} ${micState === 'transcribing' ? 'busy' : ''}`}
          onClick={micState === 'recording' ? stopListening : startListening}
          disabled={micDisabled && micState !== 'recording'}
        >
          {micState === 'transcribing' ? (
            <span className="mic-spinner" />
          ) : (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          )}
          {micState === 'recording' && <span className="mic-pulse" />}
        </button>
      </div>
    </div>
  )
}
