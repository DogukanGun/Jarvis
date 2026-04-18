import { WebSocket } from 'ws'
import type { JarvisEvent } from '../types.js'

const ROUTER_URL = process.env.JARVIS_ROUTER_URL ?? 'ws://localhost:8888/ws/chat'

type Listener = (event: JarvisEvent) => void
type StatusListener = (connected: boolean) => void

export class JarvisClient {
  private ws: WebSocket | null = null
  private listeners = new Set<Listener>()
  private statusListeners = new Set<StatusListener>()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  connected = false

  connect(): void {
    this.ws = new WebSocket(ROUTER_URL)

    this.ws.on('open', () => {
      this.connected = true
      this.statusListeners.forEach(l => l(true))
    })

    this.ws.on('message', (raw) => {
      try {
        const event: JarvisEvent = JSON.parse(raw.toString())
        this.listeners.forEach(l => l(event))
      } catch {}
    })

    this.ws.on('close', () => {
      this.connected = false
      this.statusListeners.forEach(l => l(false))
      this.reconnectTimer = setTimeout(() => this.connect(), 2000)
    })

    this.ws.on('error', () => {
      // errors are handled by close event
    })
  }

  send(message: string, intent?: string): void {
    if (!this.ws || !this.connected) return
    this.ws.send(JSON.stringify({
      user_id: 'jarvis-cli',
      message,
      ...(intent ? { intent } : {}),
    }))
  }

  on(listener: Listener): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  onStatus(listener: StatusListener): () => void {
    this.statusListeners.add(listener)
    return () => this.statusListeners.delete(listener)
  }

  disconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
  }
}

export const jarvisClient = new JarvisClient()
