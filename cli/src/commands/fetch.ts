import type { Command, CommandContext } from '../types.js'

const fetch_: Command = {
  name: 'fetch',
  description: 'Fetch and summarize a webpage',
  usage: '/fetch <url>',
  run(args: string[], ctx: CommandContext) {
    const url = args[0]?.trim()
    if (!url) {
      ctx.addMessage({ role: 'error', content: 'Usage: /fetch <url>' })
      return
    }
    ctx.sendToJarvis(url, 'web_fetch')
  },
}

export default fetch_
