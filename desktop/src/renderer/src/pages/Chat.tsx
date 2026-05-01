import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useWebSocket, WsResponse, AgentEvent } from '../hooks/useWebSocket'
import { useSpeechRecognition } from '../hooks/useSpeechRecognition'
import { useCamera } from '../hooks/useCamera'

// ── Types ──────────────────────────────────────────────────────────────────

type Message = {
  id: string
  role: 'user' | 'assistant' | 'error'
  content: string
  displayedContent: string
  isTyping: boolean
  timestamp: number
}

type LogEntry = {
  id: string
  text: string
  ts: number
}

type TaskWindowStatus = 'running' | 'completed' | 'failed'

type TaskWindowEntry = {
  id: string
  kind: 'event' | 'finding' | 'tool' | 'result'
  text: string
  ts: number
}

type TaskWindow = {
  taskId: string
  agent: string
  label: string
  status: TaskWindowStatus
  entries: TaskWindowEntry[]
  toolsUsed: string[]
}

// ── Panel component ────────────────────────────────────────────────────────

function Panel({
  label,
  accent = '#4ade80',
  children,
  className,
}: {
  label: string
  accent?: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={`hud-panel ${className ?? ''}`}>
      <div className="hud-panel-header" style={{ '--accent': accent } as React.CSSProperties}>
        <span className="hud-panel-dot" style={{ background: accent }} />
        <span className="hud-panel-label">{label}</span>
      </div>
      <div className="hud-panel-body">{children}</div>
    </div>
  )
}

// ── Task window panel ──────────────────────────────────────────────────────

const STATUS_ACCENT: Record<TaskWindowStatus, string> = {
  running: '#f59e0b',
  completed: '#4ade80',
  failed: '#f87171',
}

const ENTRY_ICONS: Record<TaskWindowEntry['kind'], string> = {
  event: '◆',
  tool: '⚙',
  finding: '▸',
  result: '✓',
}

function TaskWindowPanel({
  window: win,
  onClose,
}: {
  window: TaskWindow
  onClose: () => void
}) {
  const bodyRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: 'smooth' })
  }, [win.entries.length])

  const accent = STATUS_ACCENT[win.status]

  return (
    <div className="task-window hud-panel">
      <div className="hud-panel-header" style={{ '--accent': accent } as React.CSSProperties}>
        <span className="hud-panel-dot" style={{ background: accent }} />
        <span className="hud-panel-label">{win.label}</span>
        <span className="task-window-status">{win.status.toUpperCase()}</span>
        <button className="task-window-close" onClick={onClose} aria-label="Close">✕</button>
      </div>
      <div className="task-window-body" ref={bodyRef}>
        {win.entries.map((entry) => (
          <div key={entry.id} className={`task-entry task-entry-${entry.kind}`}>
            <span className="task-entry-icon">{ENTRY_ICONS[entry.kind]}</span>
            <span className="task-entry-text">{entry.text}</span>
          </div>
        ))}
        {win.status === 'running' && (
          <div className="task-entry task-entry-event task-entry-pulse">
            <span className="task-entry-icon">◌</span>
            <span className="task-entry-text">Processing…</span>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

export default function Chat({
  userId = 'admin',
  onGuardMode,
}: {
  userId?: string
  onGuardMode?: () => void
}): React.JSX.Element {
  const [messages, setMessages] = useState<Message[]>([])
  const [toolLog, setToolLog] = useState<LogEntry[]>([])
  const [taskWindows, setTaskWindows] = useState<TaskWindow[]>([])
  const [waiting, setWaiting] = useState(false)
  const [textInput, setTextInput] = useState('')

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const toolLogEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Status → tool log (not chat)
  const onStatus = useCallback((text: string) => {
    setToolLog((prev) => {
      const entry: LogEntry = { id: crypto.randomUUID(), text, ts: Date.now() }
      const next = [...prev, entry]
      return next.length > 60 ? next.slice(-60) : next
    })
  }, [])

  const onResponse = useCallback((data: WsResponse) => {
    setWaiting(false)
    setToolLog([]) // clear tool log when response arrives
    setMessages((prev) => {
      const finalized = prev.map((m) =>
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
          timestamp: Date.now(),
        },
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
          role: 'error',
          content: `Error: ${text}`,
          displayedContent: `Error: ${text}`,
          isTyping: false,
          timestamp: Date.now(),
        },
      ]
    })
  }, [])

  const onAgentEvent = useCallback((event: AgentEvent) => {
    const taskId = event.task_id ?? event.thread_id ?? crypto.randomUUID()
    const agent = event.sender ?? 'agent'
    const label = agent.replace(/-/g, '_').toUpperCase()

    setTaskWindows((prev) => {
      const existing = prev.find((w) => w.taskId === taskId)

      if (event.event_type === 'task.started') {
        if (existing) return prev
        const newWindow: TaskWindow = {
          taskId, agent, label,
          status: 'running',
          entries: [{ id: crypto.randomUUID(), kind: 'event', text: 'Task started', ts: Date.now() }],
          toolsUsed: [],
        }
        return [...prev, newWindow]
      }

      if (!existing) return prev

      const addEntry = (kind: TaskWindowEntry['kind'], text: string): TaskWindowEntry => ({
        id: crypto.randomUUID(), kind, text, ts: Date.now(),
      })

      if (event.event_type === 'result.security_scan') {
        const data = event.data ?? {}
        const findings: any[] = data.findings ?? []
        const toolsUsed: string[] = data.tools_used ?? []
        const newEntries: TaskWindowEntry[] = []
        if (toolsUsed.length) newEntries.push(addEntry('tool', `Tools: ${toolsUsed.join(', ')}`))
        findings.slice(0, 8).forEach((f) => {
          const desc = typeof f === 'string' ? f : (f.description ?? f.type ?? JSON.stringify(f))
          newEntries.push(addEntry('finding', String(desc).slice(0, 120)))
        })
        return prev.map((w) =>
          w.taskId === taskId
            ? { ...w, entries: [...w.entries, ...newEntries], toolsUsed: [...new Set([...w.toolsUsed, ...toolsUsed])] }
            : w
        )
      }

      if (event.event_type === 'task.completed') {
        const tools: string[] = event.tools_used ?? []
        const findings: any[] = event.findings ?? []
        const newEntries: TaskWindowEntry[] = []
        if (tools.length) newEntries.push(addEntry('tool', `Tools used: ${tools.join(', ')}`))
        findings.slice(0, 6).forEach((f) => {
          const desc = typeof f === 'string' ? f : (f.description ?? f.type ?? JSON.stringify(f))
          newEntries.push(addEntry('finding', String(desc).slice(0, 120)))
        })
        if (event.response) newEntries.push(addEntry('result', event.response.slice(0, 200)))
        newEntries.push(addEntry('event', 'Task completed'))
        return prev.map((w) =>
          w.taskId === taskId
            ? { ...w, status: 'completed', entries: [...w.entries, ...newEntries], toolsUsed: [...new Set([...w.toolsUsed, ...tools])] }
            : w
        )
      }

      if (event.event_type === 'task.failed') {
        return prev.map((w) =>
          w.taskId === taskId
            ? { ...w, status: 'failed', entries: [...w.entries, addEntry('event', `Failed: ${event.error ?? 'unknown error'}`)] }
            : w
        )
      }

      return prev
    })
  }, [])

  const { status, send } = useWebSocket({ onStatus, onResponse, onError, onAgentEvent })
  const { videoRef, active: cameraActive, capture, startCamera, stopCamera } = useCamera()

  const addLocalMessage = useCallback((content: string, role: 'assistant' | 'user' = 'assistant') => {
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role, content, displayedContent: content, isTyping: false, timestamp: Date.now() },
    ])
  }, [])

  const sendMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || waiting || status !== 'connected') return

      // ── Camera control commands (handled locally, not sent to router) ──
      const lower = trimmed.toLowerCase()
      const isStopCam = /\b(stop|close|off|disable|hide|turn off)\b.{0,15}\b(cam|camera|feed)\b/.test(lower)
      const isStartCam = /\b(start|open|on|enable|show|turn on)\b.{0,15}\b(cam|camera|feed)\b/.test(lower)

      if (isStopCam || isStartCam) {
        addLocalMessage(trimmed, 'user')
        if (isStopCam) {
          stopCamera()
          addLocalMessage('Camera feed stopped.')
        } else {
          startCamera()
          addLocalMessage('Camera feed started.')
        }
        return
      }

      const frame = cameraActive ? capture() : null

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'user',
          content: trimmed,
          displayedContent: trimmed,
          isTyping: false,
          timestamp: Date.now(),
        },
      ])
      setWaiting(true)
      send(userId, trimmed, frame ?? undefined)
    },
    [waiting, status, send, userId, cameraActive, capture, startCamera, stopCamera, addLocalMessage]
  )

  const { micState, supported, startListening, stopListening } = useSpeechRecognition(sendMessage)

  const submitText = useCallback(() => {
    const trimmed = textInput.trim()
    if (!trimmed) return
    sendMessage(trimmed)
    setTextInput('')
    inputRef.current?.focus()
  }, [textInput, sendMessage])

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        submitText()
      }
    },
    [submitText]
  )

  // Auto-focus input when response arrives
  useEffect(() => {
    if (!waiting && status === 'connected') {
      inputRef.current?.focus()
    }
  }, [waiting, status])

  // Typing animation
  useEffect(() => {
    const typingIdx = messages.findLastIndex((m) => m.isTyping)
    if (typingIdx === -1) return
    const typingMsg = messages[typingIdx]
    const interval = setInterval(() => {
      setMessages((prev) =>
        prev.map((m) => {
          if (m.id !== typingMsg.id || !m.isTyping) return m
          const nextLen = m.displayedContent.length + 3 // faster: 3 chars/tick
          if (nextLen >= m.content.length) {
            return { ...m, displayedContent: m.content, isTyping: false }
          }
          return { ...m, displayedContent: m.content.slice(0, nextLen) }
        })
      )
    }, 16)
    return () => clearInterval(interval)
  }, [messages])

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    toolLogEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [toolLog])

  const micDisabled = !supported || status !== 'connected' || waiting || micState === 'transcribing'

  return (
    <div className="chat-page">
      <div className="chat-layout">

        {/* ── Left: chat panel ──────────────────────────────────── */}
        <Panel
          label={status === 'connected' ? 'JARVIS · CHAT_LOG' : status === 'connecting' ? 'JARVIS · CONNECTING…' : 'JARVIS · OFFLINE'}
          accent={status === 'connected' ? '#4ade80' : '#666'}
          className="chat-panel"
        >
          <div className="chat-messages">
            {messages.length === 0 && status === 'connected' && (
              <div className="chat-empty">AWAITING INPUT</div>
            )}
            {messages.length === 0 && status !== 'connected' && (
              <div className="chat-empty">WAITING FOR ROUTER · :8888</div>
            )}

            {messages.map((msg) => (
              <div key={msg.id} className={`chat-msg ${msg.role}`}>
                {msg.role === 'user' && (
                  <span className="chat-msg-prefix">&gt;&nbsp;</span>
                )}
                {msg.role === 'assistant' ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.displayedContent}
                  </ReactMarkdown>
                ) : (
                  <span>{msg.content}</span>
                )}
                {msg.isTyping && <span className="chat-cursor">▌</span>}
              </div>
            ))}

            {waiting && toolLog.length === 0 && (
              <div className="chat-msg status">
                <span className="chat-thinking-dots">
                  <span /><span /><span />
                </span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input row */}
          <div className="chat-input-bar">
            <div className="chat-text-row">
              <span className="input-prompt">&gt;</span>
              <input
                ref={inputRef}
                className="chat-text-input"
                type="text"
                placeholder={waiting ? 'processing…' : 'enter command…'}
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                onKeyDown={onKeyDown}
                disabled={waiting || status !== 'connected'}
                autoComplete="off"
                spellCheck={false}
              />
              <button
                className="chat-send-button"
                onClick={submitText}
                disabled={!textInput.trim() || waiting || status !== 'connected'}
                aria-label="Send"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
              <button
                className={`mic-button ${micState === 'recording' ? 'active' : ''} ${micState === 'transcribing' ? 'busy' : ''}`}
                onClick={micState === 'recording' ? stopListening : startListening}
                disabled={micDisabled && micState !== 'recording'}
                title={micState === 'recording' ? 'Stop' : 'Speak'}
              >
                {micState === 'transcribing' ? (
                  <span className="mic-spinner" />
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
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
        </Panel>

        {/* ── Right: sidebar panels ────────────────────────────── */}
        <div className="chat-sidebar">

          {/* Guard mode button lives at the top of the sidebar */}
          {onGuardMode && (
            <button className="guard-mode-btn" onClick={onGuardMode}>
              GUARD_MODE
            </button>
          )}

          <Panel label="CAM_FEED" accent={cameraActive ? '#4ade80' : '#444'} className="cam-panel">
            <div className="cam-body">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="cam-feed"
                style={{ display: cameraActive ? 'block' : 'none' }}
              />
              {!cameraActive && (
                <div className="cam-no-signal">
                  <span>NO_SIGNAL</span>
                </div>
              )}
              <div className="cam-overlay">
                <span className="cam-status">{cameraActive ? 'LIVE' : 'OFF'}</span>
                <span className="cam-ts">{new Date().toLocaleTimeString('en-US', { hour12: false })}</span>
              </div>
            </div>
          </Panel>

          <Panel label="TOOL_OUTPUT" accent={waiting ? '#f59e0b' : '#4ade80'} className="tool-panel">
            <div className="tool-log">
              {toolLog.length === 0 && (
                <div className="tool-log-idle">— IDLE —</div>
              )}
              {toolLog.map((entry) => (
                <div key={entry.id} className="tool-log-line">
                  <span className="tool-log-arrow">&gt;</span> {entry.text}
                </div>
              ))}
              <div ref={toolLogEndRef} />
            </div>
          </Panel>

          {/* ── Task windows ── */}
          {taskWindows.map((win) => (
            <TaskWindowPanel
              key={win.taskId}
              window={win}
              onClose={() => setTaskWindows((prev) => prev.filter((w) => w.taskId !== win.taskId))}
            />
          ))}

        </div>
      </div>
    </div>
  )
}
