import React from 'react'
import { Box, Text } from 'ink'

interface Props {
  connected: boolean
  planMode: boolean
}

export default function StatusBar({ connected, planMode }: Props) {
  return (
    <Box borderStyle="single" borderBottom paddingX={1} justifyContent="space-between">
      <Text bold color="cyan">JARVIS</Text>
      <Box gap={2}>
        {planMode && <Text color="yellow" bold>[PLAN MODE]</Text>}
        <Text color={connected ? 'green' : 'red'}>
          {connected ? '● ws:ok' : '○ ws:off'}
        </Text>
      </Box>
    </Box>
  )
}
