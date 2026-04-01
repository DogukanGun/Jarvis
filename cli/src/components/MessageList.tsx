import React from 'react'
import { Box, Text } from 'ink'
import type { ChatMessage } from '../types.js'

interface Props {
  messages: ChatMessage[]
}

function roleColor(role: ChatMessage['role']): string {
  switch (role) {
    case 'user': return 'cyan'
    case 'assistant': return 'white'
    case 'status': return 'gray'
    case 'error': return 'red'
  }
}

function rolePrefix(role: ChatMessage['role']): string {
  switch (role) {
    case 'user': return '> '
    case 'assistant': return '  '
    case 'status': return '  '
    case 'error': return '! '
  }
}

export default function MessageList({ messages }: Props) {
  return (
    <Box flexDirection="column" flexGrow={1} paddingX={1} overflowY="hidden">
      {messages.map(msg => (
        <Box key={msg.id} flexDirection="column" marginBottom={0}>
          <Text color={roleColor(msg.role)} wrap="wrap">
            {rolePrefix(msg.role)}{msg.content}
          </Text>
          {msg.intent && (
            <Text color="gray" dimColor>    intent: {msg.intent}</Text>
          )}
          {msg.tools && msg.tools.length > 0 && (
            <Text color="gray" dimColor>    tools: {msg.tools.join(', ')}</Text>
          )}
          {msg.durationMs !== undefined && (
            <Text color="gray" dimColor>    {(msg.durationMs / 1000).toFixed(1)}s</Text>
          )}
        </Box>
      ))}
    </Box>
  )
}
