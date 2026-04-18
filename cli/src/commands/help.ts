import type { Command, CommandContext } from '../types.js'

const help: Command = {
  name: 'help',
  description: 'Show available commands',
  usage: '/help',
  run(_args: string[], ctx: CommandContext) {
    ctx.addMessage({
      role: 'status',
      content: [
        'Available commands:',
        '  /plan [description]  — Show or create a plan (toggle plan mode)',
        '  /research <topic>    — Run a deep research task',
        '  /scan [target]       — Run a security scan',
        '  /fetch <url>         — Fetch and summarize a webpage',
        '  /memory [query]      — Search episodic memory',
        '  /clear               — Clear chat history',
        '  /help                — Show this help message',
      ].join('\n'),
    })
  },
}

export default help
