'use client'

import { motion } from 'framer-motion'
import { TrendingUp, Search, Shield, FileText, Code2, Brain } from 'lucide-react'

const features = [
  {
    icon: TrendingUp,
    title: 'Trade Solana',
    body: 'Swap tokens, launch on Pump.fun, or let Jarvis trade automatically with a budget you control and a safety net that sells everything if something goes wrong.',
  },
  {
    icon: Search,
    title: 'Research Anything',
    body: 'Give Jarvis a topic and walk away. It crawls the web, reads sources, and delivers a structured report — like having a research assistant on call.',
  },
  {
    icon: Shield,
    title: 'Guard Your Laptop',
    body: 'When you step away, Jarvis watches through your camera. Motion detected? Alarm sounds, screen locks, you get notified.',
  },
  {
    icon: FileText,
    title: 'Read Legal Docs',
    body: "Drop in any contract or PDF. Ask questions in plain English. Jarvis finds the clauses that matter so you don't have to read 60 pages of fine print.",
  },
  {
    icon: Code2,
    title: 'Review Your Code',
    body: 'Paste a file or a whole repo. Jarvis spots bugs, security holes, and quality issues — and explains exactly what to fix.',
  },
  {
    icon: Brain,
    title: 'Remembers Everything',
    body: 'Jarvis keeps a memory of every conversation, decision, and task. The longer you use it, the better it knows you.',
  },
]

export default function Features() {
  return (
    <section className="py-32 px-6">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <p className="text-xs text-[#4ade80] tracking-[0.2em] uppercase font-medium mb-4">
            Capabilities
          </p>
          <h2 className="font-display font-bold text-4xl md:text-5xl text-[#f0f0f0]">
            What Jarvis does for you
          </h2>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map(({ icon: Icon, title, body }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 36 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.55, delay: i * 0.07 }}
              whileHover={{ y: -5, transition: { duration: 0.18 } }}
              className="group relative rounded-2xl border border-[rgba(74,222,128,0.1)] bg-[rgba(74,222,128,0.025)] p-7 hover:border-[rgba(74,222,128,0.3)] hover:bg-[rgba(74,222,128,0.055)] hover:shadow-[0_0_32px_rgba(74,222,128,0.07)] transition-all cursor-default overflow-hidden"
            >
              {/* Corner accent lines */}
              <div className="absolute top-0 left-0 w-10 h-[1px] bg-[#4ade80] opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="absolute top-0 left-0 w-[1px] h-10 bg-[#4ade80] opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="absolute bottom-0 right-0 w-10 h-[1px] bg-[#4ade80] opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="absolute bottom-0 right-0 w-[1px] h-10 bg-[#4ade80] opacity-0 group-hover:opacity-100 transition-opacity" />

              <div className="w-11 h-11 rounded-xl bg-[rgba(74,222,128,0.08)] border border-[rgba(74,222,128,0.18)] flex items-center justify-center mb-5">
                <Icon size={20} className="text-[#4ade80]" />
              </div>
              <h3 className="font-display font-bold text-lg text-[#f0f0f0] mb-2">{title}</h3>
              <p className="text-[#5a5a5a] text-sm leading-relaxed">{body}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
