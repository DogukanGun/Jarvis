import React, { useState } from 'react'
import { hasPassword } from '../lib/auth.js'
import AuthSetup from './AuthSetup.js'
import AuthPrompt from './AuthPrompt.js'
import REPL from './REPL.js'

type Screen = 'setup' | 'prompt' | 'repl'

function getInitialScreen(): Screen {
  return hasPassword() ? 'prompt' : 'setup'
}

export default function App() {
  const [screen, setScreen] = useState<Screen>(getInitialScreen)

  if (screen === 'setup') {
    return <AuthSetup onDone={() => setScreen('repl')} />
  }

  if (screen === 'prompt') {
    return <AuthPrompt onVerified={() => setScreen('repl')} />
  }

  return <REPL />
}
