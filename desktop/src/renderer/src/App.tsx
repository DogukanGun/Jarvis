import { useState } from 'react'
import './styles/globals.css'
import VisualCheck from './pages/VisualCheck'
import Chat from './pages/Chat'
import GuardMode from './pages/GuardMode'

type Page = 'visual-check' | 'chat' | 'guard'

function App(): React.JSX.Element {
  const [page, setPage] = useState<Page>('visual-check')

  if (page === 'guard') {
    return <GuardMode onDeactivate={() => setPage('chat')} />
  }

  if (page === 'chat') {
    return <Chat onGuardMode={() => setPage('guard')} />
  }

  return <VisualCheck onVerified={() => setPage('chat')} />
}

export default App
