import React, { useState } from 'react'
import { Box, Text } from 'ink'
import TextInput from 'ink-text-input'
import { setPassword } from '../lib/auth.js'

interface Props {
  onDone: () => void
}

export default function AuthSetup({ onDone }: Props) {
  const [step, setStep] = useState<'password' | 'confirm' | 'saving'>('password')
  const [password, setPasswordVal] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [inputVal, setInputVal] = useState('')

  const handleSubmitPassword = (val: string) => {
    if (val.length < 4) {
      setError('Password must be at least 4 characters.')
      setInputVal('')
      return
    }
    setPasswordVal(val)
    setError('')
    setInputVal('')
    setStep('confirm')
  }

  const handleSubmitConfirm = async (val: string) => {
    if (val !== password) {
      setError('Passwords do not match. Try again.')
      setInputVal('')
      setStep('password')
      setPasswordVal('')
      return
    }
    setConfirm(val)
    setStep('saving')
    await setPassword(password)
    onDone()
  }

  return (
    <Box flexDirection="column" padding={1} gap={1}>
      <Text bold color="cyan">JARVIS — First Run Setup</Text>
      <Text>No password set. Please create a password to protect access.</Text>

      {error && <Text color="red">{error}</Text>}

      {step === 'password' && (
        <Box gap={1}>
          <Text>New password: </Text>
          <TextInput
            value={inputVal}
            onChange={setInputVal}
            onSubmit={handleSubmitPassword}
            mask="*"
          />
        </Box>
      )}

      {step === 'confirm' && (
        <Box gap={1}>
          <Text>Confirm password: </Text>
          <TextInput
            value={inputVal}
            onChange={setInputVal}
            onSubmit={handleSubmitConfirm}
            mask="*"
          />
        </Box>
      )}

      {step === 'saving' && <Text color="gray">Saving...</Text>}
    </Box>
  )
}
