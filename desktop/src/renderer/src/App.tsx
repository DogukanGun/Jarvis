import { useState } from 'react'
import './styles/globals.css'
import VisualCheck from './pages/VisualCheck'
import Chat from './pages/Chat'

function App(): React.JSX.Element {
  const [page, setPage] = useState<'visual-check' | 'chat'>('visual-check')

  if (page === 'chat') {
    return <Chat />
  }

  return <VisualCheck onVerified={() => setPage('chat')} />
}

export default App
