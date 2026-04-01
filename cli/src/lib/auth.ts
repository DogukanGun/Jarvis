import bcrypt from 'bcryptjs'
import { loadConfig, saveConfig } from './config.js'

export function hasPassword(): boolean {
  return !!loadConfig().passwordHash
}

export async function setPassword(password: string): Promise<void> {
  const hash = await bcrypt.hash(password, 12)
  const config = loadConfig()
  saveConfig({ ...config, passwordHash: hash })
}

export async function verifyPassword(password: string): Promise<boolean> {
  const config = loadConfig()
  if (!config.passwordHash) return false
  return bcrypt.compare(password, config.passwordHash)
}

export function clearPassword(): void {
  const config = loadConfig()
  delete config.passwordHash
  saveConfig(config)
}
