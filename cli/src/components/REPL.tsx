import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { Box, useApp, useInput } from 'ink'
import { nanoid } from 'nanoid'
import type { ChatMessage, CommandContext, JarvisEvent } from '../types.js'
import { jarvisClient } from '../lib/jarvisWS.js'
import { savePlan } from '../lib/plan.js'
import { dispatch, COMMANDS } from '../commands/index.js'
import StatusBar from './StatusBar.js'
import MessageList from './MessageList.js'
import InputBar from './InputBar.js'
import CommandPalette from './CommandPalette.js'

// Heuristic: detect obvious non-chat intents so the router can skip its
// classify LLM call (saves ~1-2s per message). Errs on the side of "chat"
// — the router's classifier is the authority; this is just a fast-path hint.
const RESEARCH_RE = /\b(research|investigate|find out|look up|explain|what is|who is|history of|how does)\b/i
const FETCH_RE    = /\b(fetch|open|visit|browse|check|read|summarize)\s+https?:\/\//i
const SECURITY_RE = /\b(scan|hack|pentest|vulnerability|exploit|nmap|enumerate|port scan)\b/i

function inferIntent(msg: string): string | undefined {
  if (SECURITY_RE.test(msg)) return 'security'
  if (FETCH_RE.test(msg))    return 'web_fetch'
  if (RESEARCH_RE.test(msg)) return 'research'
  return 'chat'
}

export default function REPL() {
  const { exit } = useApp()
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: nanoid(), role: 'status', content: 'Connected to Jarvis. Type /help for commands.' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [planMode, setPlanMode] = useState(false)
  const [connected, setConnected] = useState(jarvisClient.connected)
  const [paletteIndex, setPaletteIndex] = useState(0)
  const planModeRef = useRef(planMode)

  useEffect(() => { planModeRef.current = planMode }, [planMode])

  // Compute filtered command list whenever input changes
  const paletteCommands = useMemo(() => {
    if (!input.startsWith('/')) return []
    const filter = input.slice(1).toLowerCase()
    // Close palette once the command name is fully typed and followed by a space
    if (filter.includes(' ')) return []
    return COMMANDS.filter(cmd => cmd.name.startsWith(filter))
  }, [input])

  const paletteOpen = paletteCommands.length > 0 && !loading

  // Reset selection when the filtered list changes
  useEffect(() => { setPaletteIndex(0) }, [paletteCommands.length])

  // Keyboard: handle palette navigation + selection
  useInput((_, key) => {
    if (!paletteOpen) return

    if (key.upArrow) {
      setPaletteIndex(i => Math.max(0, i - 1))
    } else if (key.downArrow) {
      setPaletteIndex(i => Math.min(paletteCommands.length - 1, i + 1))
    } else if (key.tab || key.return) {
      const cmd = paletteCommands[paletteIndex]
      if (cmd) setInput(`/${cmd.name} `)
    } else if (key.escape) {
      setInput('')
    }
  })

  useEffect(() => {
    jarvisClient.connect()
    const offStatus = jarvisClient.onStatus(setConnected)

    const offMsg = jarvisClient.on((event: JarvisEvent) => {
      if (event.type === 'status' || event.type === 'agent_event') {
        const content = event.content ?? event.event_type ?? 'Processing...'
        setMessages(prev => {
          const last = prev[prev.length - 1]
          if (last && last.role === 'status' && !last.content.startsWith('Connected')) {
            return [...prev.slice(0, -1), { ...last, content }]
          }
          return [...prev, { id: nanoid(), role: 'status', content }]
        })
      } else if (event.type === 'response') {
        const content = event.content ?? ''
        if (planModeRef.current && content) savePlan(content)
        setMessages(prev => [
          ...prev.filter(m => m.role !== 'status' || m.content.startsWith('Connected')),
          {
            id: nanoid(),
            role: 'assistant',
            content,
            intent: event.intent,
            tools: event.tools_used,
            durationMs: event.duration_ms,
          },
        ])
        setLoading(false)
      } else if (event.type === 'error') {
        setMessages(prev => [
          ...prev.filter(m => m.role !== 'status' || m.content.startsWith('Connected')),
          { id: nanoid(), role: 'error', content: event.content ?? 'Unknown error' },
        ])
        setLoading(false)
      }
    })

    return () => {
      offStatus()
      offMsg()
      jarvisClient.disconnect()
    }
  }, [])

  const addMessage = useCallback((msg: Omit<ChatMessage, 'id'>) => {
    setMessages(prev => [...prev, { id: nanoid(), ...msg }])
  }, [])

  const sendToJarvis = useCallback((text: string, intent?: string) => {
    if (!jarvisClient.connected) {
      addMessage({ role: 'error', content: 'Not connected to Jarvis router.' })
      return
    }
    setLoading(true)
    jarvisClient.send(text, intent)
  }, [addMessage])

  const togglePlanMode = useCallback(() => setPlanMode(prev => !prev), [])

  const clearHistory = useCallback(() => {
    setMessages([{ id: nanoid(), role: 'status', content: 'History cleared.' }])
  }, [])

  const handleSubmit = useCallback((val: string) => {
    const trimmed = val.trim()
    if (!trimmed) return
    setInput('')

    if (trimmed === '/exit' || trimmed === '/quit') { exit(); return }

    const ctx: CommandContext = {
      addMessage,
      sendToJarvis,
      togglePlanMode,
      isPlanMode: planModeRef.current,
      clearHistory,
    }

    if (dispatch(trimmed, ctx)) return

    addMessage({ role: 'user', content: trimmed })
    sendToJarvis(trimmed, planModeRef.current ? undefined : inferIntent(trimmed))
  }, [addMessage, sendToJarvis, togglePlanMode, clearHistory, exit])

  return (
    <Box flexDirection="column" height="100%">
      <StatusBar connected={connected} planMode={planMode} />
      <MessageList messages={messages} />
      {paletteOpen && (
        <CommandPalette
          commands={paletteCommands}
          selectedIndex={paletteIndex}
        />
      )}
      <InputBar
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
        loading={loading}
        planMode={planMode}
        paletteOpen={paletteOpen}
      />
    </Box>
  )
}
