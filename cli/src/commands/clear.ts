import type { Command, CommandContext } from '../types.js'

const clear: Command = {
  name: 'clear',
  description: 'Clear chat history',
  usage: '/clear',
  run(_args: string[], ctx: CommandContext) {
    ctx.clearHistory()
    ctx.addMessage({ role: 'status', content: 'Chat history cleared.' })
  },
}

export default clear
