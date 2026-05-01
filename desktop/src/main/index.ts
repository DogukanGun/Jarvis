import { app, shell, BrowserWindow, ipcMain, systemPreferences, session, globalShortcut, screen } from 'electron'
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
  let guardOverlays: BrowserWindow[] = []

  const GUARD_SHORTCUTS = [
    'Cmd+Tab', 'Cmd+`', 'Cmd+Q', 'Cmd+H', 'Cmd+M', 'Cmd+W',
    'Cmd+Space', 'Cmd+Option+Esc',
    'F11', 'Control+Up', 'Control+Down', 'Control+Left', 'Control+Right',
  ]

  function registerGuardShortcuts(): void {
    GUARD_SHORTCUTS.forEach((acc) => {
      try { globalShortcut.register(acc, () => {}) } catch { /* ignore */ }
    })
  }

  function unregisterGuardShortcuts(): void {
    GUARD_SHORTCUTS.forEach((acc) => {
      try { globalShortcut.unregister(acc) } catch { /* ignore */ }
    })
  }

  function findMainWindow(): BrowserWindow | undefined {
    return BrowserWindow.getAllWindows().find((w) => !guardOverlays.includes(w))
  }

  function createGuardOverlays(): void {
    const onUnlockPressed = (): void => {
      const mainWin = findMainWindow()
      if (!mainWin) return

      guardOverlays.forEach((w) => { if (!w.isDestroyed()) w.hide() })
      unregisterGuardShortcuts()
      ipcMain.removeAllListeners('guard-overlay-unlock')

      mainWin.webContents.send('guard-combo-matched')
      mainWin.restore()
      mainWin.show()
      mainWin.setAlwaysOnTop(true, 'screen-saver')
      mainWin.focus()
    }

    ipcMain.on('guard-overlay-unlock', onUnlockPressed)

    const overlayHtml = `<!DOCTYPE html>
      <html>
      <head><meta charset="utf-8">
      <style>
        * { margin: 0; padding: 0; }
        body { background: transparent; height: 100vh; overflow: hidden; cursor: default; }
      </style>
      </head>
      <body></body>
      </html>`

    const preloadPath = join(__dirname, '../preload/guardOverlay.js')

    for (const display of screen.getAllDisplays()) {
      const { x, y, width, height } = display.bounds

      const overlay = new BrowserWindow({
        x,
        y,
        width,
        height,
        transparent: true,
        frame: false,
        alwaysOnTop: true,
        skipTaskbar: true,
        focusable: true,
        hasShadow: false,
        resizable: false,
        movable: false,
        minimizable: false,
        closable: false,
        fullscreenable: false,
        webPreferences: {
          nodeIntegration: false,
          contextIsolation: true,
          preload: preloadPath,
        },
      })
      overlay.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(overlayHtml)}`)
      overlay.setIgnoreMouseEvents(false)
      overlay.setAlwaysOnTop(true, 'screen-saver')
      overlay.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true, skipTransformProcessType: true })

      guardOverlays.push(overlay)
    }
  }

  ipcMain.on('guard-alarm-triggered', () => {
    const mainWin = findMainWindow()
    if (!mainWin) return

    // Hide overlays and bring main window forward — same as unlock, but sends alarm
    guardOverlays.forEach((w) => { if (!w.isDestroyed()) w.hide() })
    unregisterGuardShortcuts()
    ipcMain.removeAllListeners('guard-overlay-unlock')

    mainWin.restore()
    mainWin.show()
    mainWin.setAlwaysOnTop(true, 'screen-saver')
    mainWin.focus()
    mainWin.webContents.send('guard-alarm')
  })

  ipcMain.on('guard-activate', () => {
    const mainWin = findMainWindow()

    if (guardOverlays.length === 0) {
      createGuardOverlays()
    } else {
      // Idempotent: re-show hidden overlays
      guardOverlays.forEach((w) => { if (!w.isDestroyed() && !w.isVisible()) w.show() })
    }

    registerGuardShortcuts()

    // Minimize main window behind overlay
    if (mainWin) mainWin.minimize()
  })

  // Re-lock: destroy old overlays and create fresh ones so the preload
  // (and the 10s unlock timeout) restarts cleanly.
  ipcMain.on('guard-relock', () => {
    guardOverlays.forEach((w) => { if (!w.isDestroyed()) w.destroy() })
    guardOverlays = []
    ipcMain.removeAllListeners('guard-overlay-unlock')
    createGuardOverlays()
    registerGuardShortcuts()

    const mainWin = findMainWindow()
    if (mainWin) {
      mainWin.setAlwaysOnTop(false)
      mainWin.minimize()
    }
  })

  ipcMain.on('guard-show-pin', () => {
    const mainWin = findMainWindow()
    guardOverlays.forEach((w) => { if (!w.isDestroyed()) w.hide() })
    unregisterGuardShortcuts()
    if (mainWin) {
      mainWin.restore()
      mainWin.show()
      mainWin.setAlwaysOnTop(true, 'screen-saver')
      mainWin.focus()
    }
  })

  ipcMain.on('guard-deactivate', () => {
    guardOverlays.forEach((w) => { if (!w.isDestroyed()) w.destroy() })
    guardOverlays = []
    unregisterGuardShortcuts()
    ipcMain.removeAllListeners('guard-overlay-unlock')

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
