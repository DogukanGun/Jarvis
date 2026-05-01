import { ipcRenderer } from 'electron'

const UNLOCK_TIMEOUT_MS = 10_000  // alarm fires if X not pressed within 10s
const GRACE_PERIOD_MS  = 1_500   // wait before listening to mouse/click

window.addEventListener('DOMContentLoaded', () => {
  let alarmSent = false

  const sendAlarm = (): void => {
    if (alarmSent) return
    alarmSent = true
    clearTimeout(unlockTimer)
    ipcRenderer.send('guard-alarm-triggered')
  }

  const sendUnlock = (): void => {
    if (alarmSent) return   // alarm already fired, too late
    alarmSent = true        // prevent alarm from also firing
    clearTimeout(unlockTimer)
    ipcRenderer.send('guard-overlay-unlock')
  }

  // If X is not pressed within UNLOCK_TIMEOUT_MS → alarm
  const unlockTimer = setTimeout(sendAlarm, UNLOCK_TIMEOUT_MS)

  // Press X → PIN entry (cancels the timeout)
  document.addEventListener('keydown', (e) => {
    if (e.key === 'x' || e.key === 'X') sendUnlock()
  })

  // After grace period: mouse move or click also triggers alarm
  let moveTimer: ReturnType<typeof setTimeout> | null = null
  setTimeout(() => {
    document.addEventListener('mousemove', () => {
      if (moveTimer) clearTimeout(moveTimer)
      moveTimer = setTimeout(sendAlarm, 400)
    })
    document.addEventListener('click', sendAlarm)
  }, GRACE_PERIOD_MS)
})
