import { useEffect, useState } from 'react'
import './styles/globals.css'
import VisualCheck from './pages/VisualCheck'
import Chat from './pages/Chat'
import GuardSetup from './pages/GuardSetup'
import GuardMode from './pages/GuardMode'
import WalletSetup from './pages/WalletSetup'
import WalletUnlock from './pages/WalletUnlock'
import Wallet from './pages/Wallet'
import Trade from './pages/Trade'

type Page =
  | 'visual-check'
  | 'chat'
  | 'guard-setup'
  | 'guard'
  | 'wallet-setup'
  | 'wallet-unlock'
  | 'wallet'
  | 'trade'

function App(): React.JSX.Element {
  const [page, setPage] = useState<Page>('visual-check')

  // After biometric onboarding, decide whether to send the user to
  // wallet setup, unlock, or straight into chat. Runs whenever we're
  // about to land on 'chat'.
  useEffect(() => {
    if (page !== 'chat') return
    let cancelled = false
    void window.api.wallet.status().then((s) => {
      if (cancelled) return
      // Don't intercept once a wallet exists and is unlocked — chat is fine.
      if (!s.hasVault) {
        // First run: nudge to setup, but don't force it.
      }
    })
    return () => { cancelled = true }
  }, [page])

  if (page === 'guard-setup') {
    return (
      <GuardSetup
        onActivate={() => setPage('guard')}
        onCancel={() => setPage('chat')}
      />
    )
  }

  if (page === 'guard') {
    return <GuardMode onDeactivate={() => setPage('chat')} />
  }

  if (page === 'wallet-setup') {
    return <WalletSetup onReady={() => setPage('wallet')} />
  }

  if (page === 'wallet-unlock') {
    return (
      <WalletUnlock
        onUnlocked={() => setPage('wallet')}
        onWipe={() => setPage('wallet-setup')}
      />
    )
  }

  if (page === 'wallet') {
    return (
      <Wallet
        onLocked={() => setPage('wallet-unlock')}
        onOpenChat={() => setPage('chat')}
        onOpenTrade={() => setPage('trade')}
      />
    )
  }

  if (page === 'trade') {
    return <Trade onBack={() => setPage('wallet')} />
  }

  if (page === 'chat') {
    return (
      <Chat
        onGuardMode={() => setPage('guard-setup')}
        onOpenWallet={async () => {
          const s = await window.api.wallet.status()
          if (!s.hasVault) setPage('wallet-setup')
          else if (!s.isUnlocked) setPage('wallet-unlock')
          else setPage('wallet')
        }}
      />
    )
  }

  return (
    <VisualCheck
      onVerified={async () => {
        const s = await window.api.wallet.status()
        if (!s.hasVault) setPage('wallet-setup')
        else if (!s.isUnlocked) setPage('wallet-unlock')
        else setPage('chat')
      }}
    />
  )
}

export default App
