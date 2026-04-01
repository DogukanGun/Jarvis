import type { Command, CommandContext } from '../types.js'

const MEMORY_URL = process.env.JARVIS_MEMORY_URL ?? 'http://localhost:8686'

const memory: Command = {
  name: 'memory',
  description: 'Search episodic memory',
  usage: '/memory [query]',
  async run(args: string[], ctx: CommandContext) {
    const query = args.join(' ').trim() || 'recent'
    ctx.addMessage({ role: 'status', content: `Searching memory for: ${query}` })
    try {
      const url = `${MEMORY_URL}/api/query?text=${encodeURIComponent(query)}`
      const res = await fetch(url)
      if (!res.ok) {
        ctx.addMessage({ role: 'error', content: `Memory service error: ${res.status}` })
        return
      }
      const data = await res.json() as { episodes?: Array<{ content?: string; timestamp?: string }> }
      const episodes = data.episodes ?? []
      if (episodes.length === 0) {
        ctx.addMessage({ role: 'status', content: 'No memories found.' })
        return
      }
      const lines = episodes.map((ep, i) => {
        const ts = ep.timestamp ? ` [${ep.timestamp}]` : ''
        return `${i + 1}.${ts} ${ep.content ?? JSON.stringify(ep)}`
      })
      ctx.addMessage({ role: 'assistant', content: lines.join('\n') })
    } catch (err) {
      ctx.addMessage({ role: 'error', content: `Memory unavailable: ${String(err)}` })
    }
  },
}

export default memory
