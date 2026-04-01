export type Role = 'user' | 'assistant' | 'status' | 'error'

export interface ChatMessage {
  id: string
  role: Role
  content: string
  intent?: string
  tools?: string[]
  durationMs?: number
}

export interface JarvisEvent {
  type: 'status' | 'agent_event' | 'response' | 'error'
  content?: string
  intent?: string
  tools_used?: string[]
  findings?: unknown[]
  report?: unknown
  duration_ms?: number
  event_type?: string
  sender?: string
}

export interface Command {
  name: string
  description: string
  usage: string
  run: (args: string[], ctx: CommandContext) => Promise<void> | void
}

export interface CommandContext {
  addMessage: (msg: Omit<ChatMessage, 'id'>) => void
  sendToJarvis: (text: string, intent?: string) => void
  togglePlanMode: () => void
  isPlanMode: boolean
  clearHistory: () => void
}
