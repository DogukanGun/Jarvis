import type { Command, CommandContext } from '../types.js'
import plan from './plan.js'
import research from './research.js'
import scan from './scan.js'
import fetch_ from './fetch.js'
import memory from './memory.js'
import clear from './clear.js'
import help from './help.js'

export const COMMANDS: Command[] = [plan, research, scan, fetch_, memory, clear, help]

export function dispatch(input: string, ctx: CommandContext): boolean {
  if (!input.startsWith('/')) return false
  const [rawName, ...rest] = input.slice(1).trim().split(/\s+/)
  const name = rawName.toLowerCase()
  const cmd = COMMANDS.find(c => c.name === name)
  if (!cmd) {
    ctx.addMessage({ role: 'error', content: `Unknown command: /${name}. Type /help for a list.` })
    return true
  }
  void cmd.run(rest, ctx)
  return true
}
