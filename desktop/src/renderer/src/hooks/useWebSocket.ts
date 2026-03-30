import { useEffect, useRef, useState, useCallback } from 'react'

export interface WsResponse {
  content: string
  intent?: string
  tools_used?: string[]
  duration_ms?: number
  emotion?: { emotion: string; valence: number; arousal: number; confidence: number }
}

export interface UseWebSocketOptions {
  url?: string
  onStatus?: (text: string) => void
  onResponse?: (data: WsResponse) => void
  onError?: (text: string) => void
}

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected'

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    url = 'ws://localhost:8888/ws/chat',
    onStatus,
    onResponse,
    onError
  } = options

  const [status, setStatus] = useState<ConnectionStatus>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const callbacksRef = useRef({ onStatus, onResponse, onError })
  const mountedRef = useRef(true)

  useEffect(() => {
    callbacksRef.current = { onStatus, onResponse, onError }
  }, [onStatus, onResponse, onError])

  const connect = useCallback(() => {
    if (!mountedRef.current) return

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        if (mountedRef.current) setStatus('connected')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          const { onStatus, onResponse, onError } = callbacksRef.current
          switch (data.type) {
            case 'status':
              onStatus?.(data.content ?? data.message ?? '')
              break
            case 'response':
              onResponse?.(data as WsResponse)
              break
            case 'error':
              onError?.(data.content ?? data.message ?? 'Unknown error')
              break
            case 'agent_event': {
              // Kafka-forwarded async results from sub-agents
              const evType = data.event_type ?? ''
              if (evType === 'task.completed' && data.response) {
                onResponse?.({ content: data.response })
              } else if (evType === 'task.failed') {
                onError?.(data.error ?? 'Task failed')
              } else if (evType === 'task.started') {
                onStatus?.(`${data.target_agent ?? 'Agent'} working...`)
              }
              break
            }
          }
        } catch {
          // ignore non-JSON
        }
      }

      ws.onclose = () => {
        if (!mountedRef.current) return
        setStatus('disconnected')
        wsRef.current = null
        reconnectTimer.current = setTimeout(connect, 3000)
      }

      ws.onerror = () => {
        ws.close()
      }
    } catch {
      if (mountedRef.current) {
        setStatus('disconnected')
        reconnectTimer.current = setTimeout(connect, 3000)
      }
    }
  }, [url])

  useEffect(() => {
    mountedRef.current = true
    connect()

    return () => {
      mountedRef.current = false
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
      }
    }
  }, [connect])

  const send = useCallback((userId: string, message: string, visualFrame?: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const payload: Record<string, string> = { user_id: userId, message }
      if (visualFrame) payload.visual_frame = visualFrame
      wsRef.current.send(JSON.stringify(payload))
    }
  }, [])

  return { status, send }
}
