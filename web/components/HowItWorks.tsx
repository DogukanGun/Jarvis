'use client'

import { motion } from 'framer-motion'
import { Fingerprint, MessageSquare, Zap } from 'lucide-react'

const steps = [
  {
    icon: Fingerprint,
    title: 'Unlock with your fingerprint',
    body: "Touch ID verifies it's you. Your wallet and data stay encrypted on your device.",
  },
  {
    icon: MessageSquare,
    title: 'Ask in plain English',
    body: 'No commands, no prompts. Just talk to it like you would a capable colleague.',
  },
  {
    icon: Zap,
    title: 'Jarvis executes',
    body: 'Trades happen, research arrives, documents get answered. Watch it work in real time.',
  },
]

export default function HowItWorks() {
  return (
    <section className="py-32 px-6 border-y border-[rgba(74,222,128,0.07)] bg-[rgba(74,222,128,0.015)]">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <p className="text-xs text-[#4ade80] tracking-[0.2em] uppercase font-medium mb-4">
            How it works
          </p>
          <h2 className="font-display font-bold text-4xl md:text-5xl text-[#f0f0f0]">
            Three steps. That&apos;s it.
          </h2>
        </motion.div>

        <div className="relative grid md:grid-cols-3 gap-12 md:gap-6">
          {/* Connector line (desktop only) */}
          <div
            className="hidden md:block absolute top-10 left-[calc(16.67%+2.5rem)] right-[calc(16.67%+2.5rem)] h-[1px]"
            style={{
              background:
                'linear-gradient(90deg, transparent, rgba(74,222,128,0.35), rgba(74,222,128,0.35), transparent)',
            }}
          />

          {steps.map(({ icon: Icon, title, body }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 32 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: i * 0.14 }}
              className="flex flex-col items-center text-center gap-5"
            >
              <div className="relative flex-shrink-0">
                <div className="w-20 h-20 rounded-full border-2 border-[rgba(74,222,128,0.28)] bg-[rgba(74,222,128,0.05)] flex items-center justify-center">
                  <Icon size={30} className="text-[#4ade80]" />
                </div>
                <span className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-[#4ade80] text-[#0a0a0a] text-xs font-bold flex items-center justify-center">
                  {i + 1}
                </span>
              </div>
              <h3 className="font-display font-bold text-xl text-[#f0f0f0] leading-snug">
                {title}
              </h3>
              <p className="text-[#5a5a5a] text-sm leading-relaxed max-w-xs">{body}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
