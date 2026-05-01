import { spawn, type ChildProcess } from 'child_process'
import { existsSync, mkdirSync, openSync } from 'fs'
import { join, resolve } from 'path'
import { app, BrowserWindow } from 'electron'
import { startLoopback, stopLoopback, getLoopbackInfo, isLoopbackRunning } from './loopback'
import { onLockChange } from './signer'
import { loadConfig } from './config'

export type SpawnState = 'not-installed' | 'spawning' | 'running' | 'crashed' | 'stopped'

export interface AgentStatus {
  name: 'solana-trader' | 'solana-strategy'
  state: SpawnState
  port: number
  pid: number | null
  logPath: string
  logTail: string[]
  lastError: string | null
}

interface InternalAgent extends AgentStatus {
  process: ChildProcess | null
}

const TAIL_SIZE = 50

const agents: Record<'solana-trader' | 'solana-strategy', InternalAgent> = {
  'solana-trader': makeInitial('solana-trader', 8901),
  'solana-strategy': makeInitial('solana-strategy', 8902),
}

function makeInitial(name: 'solana-trader' | 'solana-strategy', port: number): InternalAgent {
  return {
    name,
    state: 'stopped',
    port,
    pid: null,
    logPath: '',
    logTail: [],
    lastError: null,
    process: null,
  }
}

function repoRoot(): string {
  let dir = app.isPackaged ? process.resourcesPath : app.getAppPath()
  for (let i = 0; i < 6; i++) {
    if (existsSync(join(dir, 'agent', 'solana-trader'))) return dir
    dir = resolve(dir, '..')
  }
  return resolve(app.getAppPath(), '..')
}

function logsDir(): string {
  const d = join(repoRoot(), 'logs')
  try { if (!existsSync(d)) mkdirSync(d, { recursive: true }) } catch { /* ignore */ }
  return d
}

function broadcast(): void {
  const snapshot = getStatusSnapshot()
  for (const win of BrowserWindow.getAllWindows()) {
    win.webContents.send('agents:status-changed', snapshot)
  }
}

function transition(name: 'solana-trader' | 'solana-strategy', state: SpawnState, lastError?: string): void {
  const a = agents[name]
  a.state = state
  if (lastError !== undefined) a.lastError = lastError
  broadcast()
}

function pushLog(name: 'solana-trader' | 'solana-strategy', text: string): void {
  const a = agents[name]
  for (const line of text.split('\n')) {
    if (!line) continue
    a.logTail.push(line)
    if (a.logTail.length > TAIL_SIZE) a.logTail.shift()
  }
  broadcast()
}

export function getStatusSnapshot(): { trader: AgentStatus; strategy: AgentStatus } {
  const strip = (a: InternalAgent): AgentStatus => ({
    name: a.name,
    state: a.state,
    port: a.port,
    pid: a.pid,
    logPath: a.logPath,
    logTail: a.logTail.slice(-TAIL_SIZE),
    lastError: a.lastError,
  })
  return {
    trader: strip(agents['solana-trader']),
    strategy: strip(agents['solana-strategy']),
  }
}

function attachIO(name: 'solana-trader' | 'solana-strategy', proc: ChildProcess): void {
  proc.stdout?.on('data', (chunk: Buffer) => pushLog(name, chunk.toString('utf-8')))
  proc.stderr?.on('data', (chunk: Buffer) => pushLog(name, chunk.toString('utf-8')))
}

function spawnTrader(env: NodeJS.ProcessEnv): boolean {
  const a = agents['solana-trader']
  const cwd = join(repoRoot(), 'agent', 'solana-trader')
  if (!existsSync(join(cwd, 'node_modules'))) {
    transition('solana-trader', 'not-installed', 'Run: cd agent/solana-trader && npm install')
    return false
  }
  a.logPath = join(logsDir(), 'solana-trader.log')
  transition('solana-trader', 'spawning', null as unknown as string)
  const out = openSync(a.logPath, 'a')
  const err = openSync(a.logPath, 'a')
  const proc = spawn('npm', ['run', 'dev'], {
    cwd,
    env: { ...process.env, ...env, PORT: String(a.port) },
    stdio: ['ignore', out, err],
    shell: false,
  })
  a.process = proc
  a.pid = proc.pid ?? null
  a.lastError = null
  // We stream stdout to file via fd above; for the in-memory tail, also attach pipes:
  // (re-spawn with 'pipe' if we want both file + pipe; simpler: just append a periodic tail-read.)
  // For now, surface only spawn errors and exit codes via the events below.
  proc.on('error', (e) => {
    pushLog('solana-trader', `[spawn error] ${e.message}`)
    transition('solana-trader', 'crashed', e.message)
  })
  proc.on('exit', (code) => {
    pushLog('solana-trader', `[exit] code=${code}`)
    a.process = null
    a.pid = null
    if (code === 0 || code === null) transition('solana-trader', 'stopped')
    else transition('solana-trader', 'crashed', `exited ${code}`)
  })
  // Mark as running optimistically; the renderer's /health poll confirms.
  setTimeout(() => {
    if (a.state === 'spawning') transition('solana-trader', 'running')
  }, 1500)
  return true
}

function pickPython(cwd: string): string {
  // Prefer the venv created by run_local.sh's setup_venv. System python3 won't
  // have FastAPI / langchain etc. installed, so we'd crash immediately.
  const venvPy = join(cwd, '.venv', 'bin', 'python')
  if (existsSync(venvPy)) return venvPy
  return 'python3'
}

function spawnStrategy(env: NodeJS.ProcessEnv): boolean {
  const a = agents['solana-strategy']
  const cwd = join(repoRoot(), 'agent', 'solana-strategy')
  if (!existsSync(join(cwd, 'app', 'server.py'))) {
    transition('solana-strategy', 'crashed', `not found at ${cwd}`)
    return false
  }
  const py = pickPython(cwd)
  if (py === 'python3' && !existsSync(join(cwd, '.venv'))) {
    transition('solana-strategy', 'not-installed', 'Run ./run_local.sh once to bootstrap the venv')
    return false
  }
  a.logPath = join(logsDir(), 'solana-strategy.log')
  transition('solana-strategy', 'spawning')
  const out = openSync(a.logPath, 'a')
  const err = openSync(a.logPath, 'a')
  const proc = spawn(py, ['run_server.py'], {
    cwd,
    env: {
      ...process.env,
      ...env,
      PORT: String(a.port),
      TRADER_BASE_URL: 'http://127.0.0.1:8901',
    },
    stdio: ['ignore', out, err],
    shell: false,
  })
  a.process = proc
  a.pid = proc.pid ?? null
  a.lastError = null
  proc.on('error', (e) => {
    pushLog('solana-strategy', `[spawn error] ${e.message}`)
    transition('solana-strategy', 'crashed', e.message)
  })
  proc.on('exit', (code) => {
    pushLog('solana-strategy', `[exit] code=${code}`)
    a.process = null
    a.pid = null
    if (code === 0 || code === null) transition('solana-strategy', 'stopped')
    else transition('solana-strategy', 'crashed', `exited ${code}`)
  })
  setTimeout(() => {
    if (a.state === 'spawning') transition('solana-strategy', 'running')
  }, 1500)
  return true
}

function killOne(name: 'solana-trader' | 'solana-strategy'): void {
  const a = agents[name]
  if (a.process) {
    try { a.process.kill('SIGTERM') } catch { /* ignore */ }
  }
  a.process = null
  a.pid = null
  transition(name, 'stopped')
}

function killAll(): void {
  killOne('solana-trader')
  killOne('solana-strategy')
}

function buildEnv(): NodeJS.ProcessEnv | null {
  if (!isLoopbackRunning()) return null
  const info = getLoopbackInfo()
  const cfg = loadConfig()
  return {
    LOOPBACK_PORT: String(info.port),
    LOOPBACK_TOKEN: info.token,
    RPC_URL: cfg.rpcUrl,
    WALLET_PUBKEY: info.publicKey,
    NETWORK: cfg.network,
  }
}

export async function startAll(): Promise<void> {
  if (!isLoopbackRunning()) {
    try { await startLoopback() } catch (e) {
      const msg = (e as Error).message
      transition('solana-trader', 'crashed', `loopback failed: ${msg}`)
      transition('solana-strategy', 'crashed', `loopback failed: ${msg}`)
      return
    }
  }
  const env = buildEnv()
  if (!env) return
  if (agents['solana-trader'].state !== 'running' && agents['solana-trader'].state !== 'spawning') {
    spawnTrader(env)
  }
  if (agents['solana-strategy'].state !== 'running' && agents['solana-strategy'].state !== 'spawning') {
    spawnStrategy(env)
  }
}

export async function restartTrader(): Promise<void> {
  killOne('solana-trader')
  await new Promise((r) => setTimeout(r, 250))
  const env = buildEnv()
  if (!env) {
    transition('solana-trader', 'crashed', 'wallet locked — unlock to restart')
    return
  }
  spawnTrader(env)
}

export async function restartStrategy(): Promise<void> {
  killOne('solana-strategy')
  await new Promise((r) => setTimeout(r, 250))
  const env = buildEnv()
  if (!env) return
  spawnStrategy(env)
}

// Run `npm install` inside agent/solana-trader; stream output via the
// provided callback. After successful install, attempt to spawn the trader.
export async function installTrader(onLog: (line: string) => void): Promise<{ ok: boolean; code: number | null }> {
  const cwd = join(repoRoot(), 'agent', 'solana-trader')
  if (!existsSync(cwd)) {
    onLog(`[install] missing dir: ${cwd}`)
    return { ok: false, code: null }
  }
  onLog(`[install] cd ${cwd}`)
  onLog('[install] npm install …')
  return new Promise((resolveP) => {
    const proc = spawn('npm', ['install'], { cwd, stdio: ['ignore', 'pipe', 'pipe'], shell: false })
    proc.stdout?.on('data', (d: Buffer) => onLog(d.toString('utf-8').trimEnd()))
    proc.stderr?.on('data', (d: Buffer) => onLog(d.toString('utf-8').trimEnd()))
    proc.on('error', (e) => {
      onLog(`[install] error: ${e.message}`)
      resolveP({ ok: false, code: null })
    })
    proc.on('exit', (code) => {
      onLog(`[install] exit ${code}`)
      if (code === 0) {
        const env = buildEnv()
        if (env) spawnTrader(env)
        resolveP({ ok: true, code })
      } else {
        resolveP({ ok: false, code })
      }
    })
  })
}

// Create venv if missing, then run `pip install -r requirements.txt` inside it.
// Streams output via the callback. After successful install, attempt to spawn
// the strategy.
export async function installStrategy(onLog: (line: string) => void): Promise<{ ok: boolean; code: number | null }> {
  const cwd = join(repoRoot(), 'agent', 'solana-strategy')
  if (!existsSync(cwd)) {
    onLog(`[install] missing dir: ${cwd}`)
    return { ok: false, code: null }
  }
  const venv = join(cwd, '.venv')
  const venvPy = join(venv, 'bin', 'python')
  const venvPip = join(venv, 'bin', 'pip')
  const reqs = join(cwd, 'requirements.txt')

  if (!existsSync(venv)) {
    onLog('[install] creating venv …')
    const created = await runStreamed('python3', ['-m', 'venv', venv], cwd, onLog)
    if (!created) {
      onLog('[install] venv create failed')
      return { ok: false, code: null }
    }
  }

  onLog('[install] upgrading pip …')
  await runStreamed(venvPy, ['-m', 'pip', 'install', '-q', '--upgrade', 'pip'], cwd, onLog)

  onLog('[install] pip install -r requirements.txt …')
  const code = await runStreamedExitCode(venvPip, ['install', '-r', reqs], cwd, onLog)
  if (code === 0) {
    const env = buildEnv()
    if (env) spawnStrategy(env)
    return { ok: true, code }
  }
  return { ok: false, code }
}

function runStreamed(
  cmd: string,
  args: string[],
  cwd: string,
  onLog: (line: string) => void,
): Promise<boolean> {
  return new Promise((resolve) => {
    const proc = spawn(cmd, args, { cwd, stdio: ['ignore', 'pipe', 'pipe'], shell: false })
    proc.stdout?.on('data', (d: Buffer) => onLog(d.toString('utf-8').trimEnd()))
    proc.stderr?.on('data', (d: Buffer) => onLog(d.toString('utf-8').trimEnd()))
    proc.on('error', (e) => { onLog(`[install] error: ${e.message}`); resolve(false) })
    proc.on('exit', (code) => resolve(code === 0))
  })
}

function runStreamedExitCode(
  cmd: string,
  args: string[],
  cwd: string,
  onLog: (line: string) => void,
): Promise<number | null> {
  return new Promise((resolve) => {
    const proc = spawn(cmd, args, { cwd, stdio: ['ignore', 'pipe', 'pipe'], shell: false })
    proc.stdout?.on('data', (d: Buffer) => onLog(d.toString('utf-8').trimEnd()))
    proc.stderr?.on('data', (d: Buffer) => onLog(d.toString('utf-8').trimEnd()))
    proc.on('error', (e) => { onLog(`[install] error: ${e.message}`); resolve(null) })
    proc.on('exit', (code) => resolve(code ?? null))
  })
}

let bound = false
export function bindAgentSpawnerToSigner(): void {
  if (bound) return
  bound = true
  // On unlock: start agents (idempotent — won't double-spawn).
  // On lock: leave agents running. They're stateless; the loopback already
  // returns 423 for /sign-tx while the wallet is locked, which is enough.
  // Killing the children every lock event tears down 10+ seconds of startup
  // (langchain imports, npm-run-dev, fastify init) for no security benefit,
  // since the keypair material lives only in signer.ts and is wiped on lock.
  onLockChange((unlocked) => {
    if (unlocked) void startAll()
  })
  app.on('before-quit', () => killAll())
}
