import { app, shell, BrowserWindow, ipcMain, systemPreferences, session } from 'electron'
import { join } from 'path'
import { homedir } from 'os'
import { readFileSync } from 'fs'
import bcrypt from 'bcryptjs'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import icon from '../../resources/icon.png?asset'

function createWindow(): void {
  const mainWindow = new BrowserWindow({
    width: 960,
    height: 720,
    show: false,
    autoHideMenuBar: true,
    title: 'Jarvis',
    ...(process.platform === 'linux' ? { icon } : {}),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
    },
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
  })

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(async () => {
  electronApp.setAppUserModelId('com.jarvis')

  // Grant camera permission to the renderer without a browser prompt
  session.defaultSession.setPermissionRequestHandler((_wc, permission, callback) => {
    if (permission === 'media') {
      callback(true)
    } else {
      callback(false)
    }
  })

  // On macOS ask the OS for camera + microphone access (shows system dialog once)
  if (process.platform === 'darwin') {
    const camStatus = await systemPreferences.askForMediaAccess('camera')
    if (!camStatus) console.warn('Camera access denied by macOS')

    const micStatus = await systemPreferences.askForMediaAccess('microphone')
    if (!micStatus) console.warn('Microphone access denied by macOS')
  }

  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  ipcMain.on('ping', () => console.log('pong'))

  ipcMain.handle('biometric-available', () => {
    if (process.platform === 'darwin') {
      return systemPreferences.canPromptTouchID()
    }
    return false
  })

  ipcMain.handle('biometric-verify', async (_event, reason: string) => {
    if (process.platform === 'darwin') {
      try {
        await systemPreferences.promptTouchID(reason)
        return true
      } catch {
        return false
      }
    }
    return false
  })

  ipcMain.on('minimize-window', () => {
    const win = BrowserWindow.getFocusedWindow() ?? BrowserWindow.getAllWindows()[0]
    if (win) win.minimize()
  })

  ipcMain.on('restore-window', () => {
    const win = BrowserWindow.getAllWindows()[0]
    if (win) {
      win.restore()
      win.show()
      win.focus()
    }
  })

  // Guard mode — fullscreen overlay to block input
  let guardOverlay: BrowserWindow | null = null

  ipcMain.on('guard-activate', () => {
    const mainWin = BrowserWindow.getAllWindows().find((w) => w !== guardOverlay)

    // Create overlay on each screen
    if (!guardOverlay) {
      const { screen } = require('electron')
      const primaryDisplay = screen.getPrimaryDisplay()
      const { width, height } = primaryDisplay.size

      guardOverlay = new BrowserWindow({
        width,
        height,
        x: 0,
        y: 0,
        fullscreen: true,
        transparent: true,
        frame: false,
        alwaysOnTop: true,
        skipTaskbar: true,
        focusable: true,
        hasShadow: false,
        resizable: false,
        webPreferences: { nodeIntegration: false },
      })
      guardOverlay.loadURL('data:text/html,<html><body style="margin:0;cursor:none;background:transparent;"></body></html>')
      guardOverlay.setIgnoreMouseEvents(false)
      guardOverlay.setAlwaysOnTop(true, 'screen-saver')

      // Listen for unlock combo on the overlay: Shift Shift Enter Enter
      const combo = ['Shift', 'Shift', 'Enter', 'Enter']
      let seq: string[] = []
      let comboTimer: ReturnType<typeof setTimeout> | null = null

      guardOverlay.webContents.on('before-input-event', (_event, input) => {
        if (input.type !== 'keyDown') return
        seq.push(input.key)
        if (comboTimer) clearTimeout(comboTimer)
        comboTimer = setTimeout(() => { seq = [] }, 2000)

        if (seq.length >= combo.length) {
          const tail = seq.slice(-combo.length)
          if (tail.every((k, i) => k === combo[i])) {
            seq = []
            // Notify renderer that combo was entered
            const mainWin = BrowserWindow.getAllWindows().find((w) => w !== guardOverlay)
            if (mainWin) {
              mainWin.webContents.send('guard-combo-matched')
              mainWin.restore()
              mainWin.show()
              mainWin.setAlwaysOnTop(true, 'screen-saver')
              mainWin.focus()
            }
          }
        }
      })
    }

    // Minimize main window behind overlay
    if (mainWin) mainWin.minimize()
  })

  ipcMain.on('guard-show-pin', () => {
    const mainWin = BrowserWindow.getAllWindows().find((w) => w !== guardOverlay)
    if (mainWin) {
      mainWin.restore()
      mainWin.show()
      mainWin.setAlwaysOnTop(true, 'screen-saver')
      mainWin.focus()
    }
  })

  ipcMain.on('guard-deactivate', () => {
    if (guardOverlay) {
      guardOverlay.destroy()
      guardOverlay = null
    }
    const mainWin = BrowserWindow.getAllWindows()[0]
    if (mainWin) {
      mainWin.setAlwaysOnTop(false)
      mainWin.restore()
      mainWin.show()
      mainWin.focus()
    }
  })

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
