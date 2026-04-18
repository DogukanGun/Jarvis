import { join } from 'path'
import { readFileSync, writeFileSync, existsSync } from 'fs'
import { CONFIG_DIR_PATH } from './config.js'

export const PLAN_FILE_PATH = join(CONFIG_DIR_PATH, 'plan.md')

export function getPlan(): string | null {
  if (!existsSync(PLAN_FILE_PATH)) return null
  const content = readFileSync(PLAN_FILE_PATH, 'utf8')
  return content.trim() || null
}

export function savePlan(content: string): void {
  writeFileSync(PLAN_FILE_PATH, content)
}

export function clearPlan(): void {
  if (existsSync(PLAN_FILE_PATH)) writeFileSync(PLAN_FILE_PATH, '')
}
