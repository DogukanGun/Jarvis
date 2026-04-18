import type { Command, CommandContext } from '../types.js'

const scan: Command = {
  name: 'scan',
  description: 'Run a security scan',
  usage: '/scan [target]',
  run(args: string[], ctx: CommandContext) {
    const target = args.join(' ').trim()
    const message = target ? `scan ${target}` : 'run a security scan'
    ctx.sendToJarvis(message, 'security')
  },
}

export default scan
