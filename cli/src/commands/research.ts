import type { Command, CommandContext } from '../types.js'

const research: Command = {
  name: 'research',
  description: 'Run a deep research task',
  usage: '/research <topic>',
  run(args: string[], ctx: CommandContext) {
    const topic = args.join(' ').trim()
    if (!topic) {
      ctx.addMessage({ role: 'error', content: 'Usage: /research <topic>' })
      return
    }
    ctx.sendToJarvis(topic, 'research')
  },
}

export default research
