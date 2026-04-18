import type { Command, CommandContext } from '../types.js'
import { getPlan, PLAN_FILE_PATH } from '../lib/plan.js'

const plan: Command = {
  name: 'plan',
  description: 'Show current plan or toggle plan mode',
  usage: '/plan [description]',
  run(args: string[], ctx: CommandContext) {
    const description = args.join(' ').trim()

    if (description) {
      // Send to Jarvis as a planning request
      ctx.addMessage({ role: 'status', content: `Creating plan: ${description}` })
      ctx.sendToJarvis(`Create a plan for: ${description}`)
      return
    }

    // No args: show current plan or toggle plan mode
    const currentPlan = getPlan()
    if (currentPlan) {
      ctx.addMessage({
        role: 'status',
        content: `Current plan (${PLAN_FILE_PATH}):\n\n${currentPlan}`,
      })
    }

    const newMode = !ctx.isPlanMode
    ctx.togglePlanMode()
    ctx.addMessage({
      role: 'status',
      content: newMode
        ? 'Plan mode ON — messages will be prefixed as planning requests.'
        : 'Plan mode OFF — back to normal chat.',
    })
  },
}

export default plan
