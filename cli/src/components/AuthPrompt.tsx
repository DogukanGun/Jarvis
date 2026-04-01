import React, { useState } from 'react'
import { Box, Text, useApp } from 'ink'
import TextInput from 'ink-text-input'
import { verifyPassword } from '../lib/auth.js'

const MAX_ATTEMPTS = 3

interface Props {
  onVerified: () => void
}

export default function AuthPrompt({ onVerified }: Props) {
  const { exit } = useApp()
  const [inputVal, setInputVal] = useState('')
  const [error, setError] = useState('')
  const [attempts, setAttempts] = useState(0)
  const [checking, setChecking] = useState(false)

  const handleSubmit = async (val: string) => {
    if (!val.trim()) return
    setInputVal('')
    setChecking(true)

    const ok = await verifyPassword(val)
    setChecking(false)

    if (ok) {
      onVerified()
      return
    }

    const newAttempts = attempts + 1
    setAttempts(newAttempts)

    if (newAttempts >= MAX_ATTEMPTS) {
      setError(`Too many failed attempts. Exiting.`)
      setTimeout(() => exit(), 1000)
      return
    }

    setError(`Wrong password. ${MAX_ATTEMPTS - newAttempts} attempt(s) remaining.`)
  }

  return (
    <Box flexDirection="column" padding={1} gap={1}>
      <Text bold color="cyan">JARVIS</Text>
      <Text>Enter your password to continue.</Text>

      {error && <Text color="red">{error}</Text>}

      {!checking && attempts < MAX_ATTEMPTS && (
        <Box gap={1}>
          <Text>Password: </Text>
          <TextInput
            value={inputVal}
            onChange={setInputVal}
            onSubmit={handleSubmit}
            mask="*"
          />
        </Box>
      )}

      {checking && <Text color="gray">Verifying...</Text>}
    </Box>
  )
}
