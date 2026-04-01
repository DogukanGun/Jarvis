import React from 'react'
import { Box, Text } from 'ink'
import type { Command } from '../types.js'

interface Props {
  commands: Command[]
  selectedIndex: number
}

export default function CommandPalette({ commands, selectedIndex }: Props) {
  if (commands.length === 0) return null

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor="cyan"
      marginX={1}
      paddingX={1}
    >
      {commands.map((cmd, i) => {
        const active = i === selectedIndex
        return (
          <Box key={cmd.name} gap={2}>
            <Text color={active ? 'cyan' : 'gray'} bold={active}>
              {active ? '›' : ' '} {'/' + cmd.name}
            </Text>
            <Text color={active ? 'white' : 'gray'}>
              {cmd.description}
            </Text>
            <Text color="gray" dimColor>
              {'  ' + cmd.usage}
            </Text>
          </Box>
        )
      })}
      <Box marginTop={0}>
        <Text color="gray" dimColor>
          ↑↓ navigate  ↵ select  esc dismiss
        </Text>
      </Box>
    </Box>
  )
}
