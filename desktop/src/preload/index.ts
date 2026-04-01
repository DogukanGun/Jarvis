import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'

const api = {
  minimizeWindow: (): void => ipcRenderer.send('minimize-window'),
  restoreWindow: (): void => ipcRenderer.send('restore-window'),
  activateGuard: (): void => ipcRenderer.send('guard-activate'),
  deactivateGuard: (): void => ipcRenderer.send('guard-deactivate'),
  showPinEntry: (): void => ipcRenderer.send('guard-show-pin'),
  onGuardCombo: (callback: () => void): (() => void) => {
    const handler = (): void => callback()
    ipcRenderer.on('guard-combo-matched', handler)
    return () => ipcRenderer.removeListener('guard-combo-matched', handler)
  },
  verifyAdminPassword: (password: string): Promise<boolean> =>
    ipcRenderer.invoke('verify-admin-password', password),
}

if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('electron', electronAPI)
    contextBridge.exposeInMainWorld('api', api)
  } catch (error) {
    console.error(error)
  }
} else {
  // @ts-ignore (define in dts)
  window.electron = electronAPI
  // @ts-ignore (define in dts)
  window.api = api
}
