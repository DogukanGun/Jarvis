import { homedir } from 'os'
import { join } from 'path'
import { mkdirSync, readFileSync, writeFileSync, existsSync } from 'fs'

export const CONFIG_DIR_PATH = join(homedir(), '.jarvis')
const CONFIG_FILE = join(CONFIG_DIR_PATH, 'config.json')

export interface JarvisConfig {
  passwordHash?: string
  routerUrl?: string
}

export function loadConfig(): JarvisConfig {
  mkdirSync(CONFIG_DIR_PATH, { recursive: true })
  if (!existsSync(CONFIG_FILE)) return {}
  try {
    return JSON.parse(readFileSync(CONFIG_FILE, 'utf8'))
  } catch {
    return {}
  }
}

export function saveConfig(config: JarvisConfig): void {
  mkdirSync(CONFIG_DIR_PATH, { recursive: true })
  writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2))
}
