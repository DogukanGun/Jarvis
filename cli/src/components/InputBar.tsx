import React from 'react'
import { Box, Text } from 'ink'
import TextInput from 'ink-text-input'
import Spinner from 'ink-spinner'

interface Props {
  value: string
  onChange: (val: string) => void
  onSubmit: (val: string) => void
  loading: boolean
  planMode: boolean
  paletteOpen: boolean
}

export default function InputBar({ value, onChange, onSubmit, loading, planMode, paletteOpen }: Props) {
  const placeholder = planMode
    ? 'Describe your plan...'
    : 'Type a message or /command'

  return (
    <Box borderStyle="single" borderTop paddingX={1} gap={1}>
      {loading ? (
        <>
          <Text color="yellow"><Spinner type="dots" /></Text>
          <Text color="gray">Thinking...</Text>
        </>
      ) : (
        <>
          <Text color="cyan" bold>{'>'}</Text>
          <TextInput
            value={value}
            onChange={onChange}
            // When palette is open, Enter selects the command — suppress normal submit
            onSubmit={paletteOpen ? () => {} : onSubmit}
            placeholder={placeholder}
          />
        </>
      )}
    </Box>
  )
}
