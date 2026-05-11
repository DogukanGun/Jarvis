'use client'

import { motion } from 'framer-motion'
import { Github, Cpu, Code2, Users } from 'lucide-react'

const pillars = [
  {
    icon: Cpu,
    title: 'Open Hardware',
    desc: 'Schematics, bill of materials, and build guides for the Jarvis smart glasses. Manufacture your own pair.',
  },
  {
    icon: Code2,
    title: 'Open Software',
    desc: 'Every agent, every integration, every line of the desktop app — MIT licensed and on GitHub.',
  },
  {
    icon: Users,
    title: 'Community Skills',
    desc: "Build a plugin that adds a capability Jarvis doesn't have yet. Share it. Install others'. The ecosystem grows together.",
  },
]

export default function OpenSource() {
  return (
    <section className="py-32 px-6">
      <div className="max-w-6xl mx-auto flex flex-col items-center gap-16">

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center max-w-2xl"
        >
          <p className="text-xs text-[#4ade80] tracking-[0.2em] uppercase font-medium mb-4">
            Open Source
          </p>
          <h2 className="font-display font-bold text-4xl md:text-5xl text-[#f0f0f0] mb-6">
            Yours to extend.
          </h2>
          <p className="text-lg text-[#5a5a5a] leading-relaxed">
            Every line of code is open. Fork it, mod it, add skills, build plugins.
            If Jarvis doesn&apos;t do something you need, you can teach it.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-6 w-full">
          {pillars.map(({ icon: Icon, title, desc }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, scale: 0.94 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="rounded-2xl border border-[rgba(74,222,128,0.1)] bg-[rgba(74,222,128,0.025)] p-8 flex flex-col gap-5"
            >
              <div className="w-12 h-12 rounded-xl bg-[rgba(74,222,128,0.08)] border border-[rgba(74,222,128,0.18)] flex items-center justify-center">
                <Icon size={22} className="text-[#4ade80]" />
              </div>
              <h3 className="font-display font-bold text-xl text-[#f0f0f0]">{title}</h3>
              <p className="text-[#5a5a5a] text-sm leading-relaxed">{desc}</p>
            </motion.div>
          ))}
        </div>

        <motion.a
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          href="https://github.com/DogukanGun/Jarvis"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-3 px-8 py-4 rounded-full border border-[rgba(74,222,128,0.3)] text-[#f0f0f0] font-semibold hover:border-[#4ade80] hover:text-[#4ade80] hover:shadow-[0_0_28px_rgba(74,222,128,0.12)] transition-all"
        >
          <Github size={20} />
          Star on GitHub
        </motion.a>
      </div>
    </section>
  )
}
