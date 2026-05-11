'use client'

import { motion } from 'framer-motion'
import { Cpu, Globe, Glasses } from 'lucide-react'

const pillars = [
  { icon: Cpu,     label: 'Open hardware',  desc: 'Schematics, BOM, and build guides — manufacture your own pair.' },
  { icon: Globe,   label: 'Open software',  desc: 'Every line of Jarvis is on GitHub. Fork it. Modify it. Ship it.' },
  { icon: Glasses, label: 'Wear your AI',   desc: 'Context-aware intelligence in your field of view, hands-free.' },
]

export default function Vision() {
  return (
    <section className="py-32 px-6 overflow-hidden">
      <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-20 items-center">

        {/* Left: copy */}
        <motion.div
          initial={{ opacity: 0, x: -40 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.75, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col gap-8"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[rgba(74,222,128,0.2)] bg-[rgba(74,222,128,0.05)] w-fit">
            <span className="w-1.5 h-1.5 rounded-full bg-[#4ade80] animate-pulse" />
            <span className="text-xs text-[#4ade80] tracking-widest uppercase font-medium">
              The Vision
            </span>
          </div>

          <h2 className="font-display font-bold text-4xl md:text-5xl leading-tight text-[#f0f0f0]">
            Built for your eyes,{' '}
            <span className="text-[#4ade80]">not just your desk.</span>
          </h2>

          <p className="text-lg text-[#666] leading-relaxed">
            Jarvis is more than software. We&apos;re building{' '}
            <strong className="text-[#f0f0f0]">open-source smart glasses</strong> —
            hardware you can manufacture yourself, software you can modify freely.
          </p>
          <p className="text-lg text-[#666] leading-relaxed">
            Wear it, extend it, own it. No subscription. No cloud dependency.
            Just intelligence that belongs to you.
          </p>

          <div className="flex flex-col gap-5">
            {pillars.map(({ icon: Icon, label, desc }) => (
              <div key={label} className="flex items-start gap-4">
                <div className="mt-0.5 w-9 h-9 rounded-xl bg-[rgba(74,222,128,0.08)] border border-[rgba(74,222,128,0.2)] flex items-center justify-center flex-shrink-0">
                  <Icon size={17} className="text-[#4ade80]" />
                </div>
                <div>
                  <p className="font-semibold text-[#f0f0f0] text-sm">{label}</p>
                  <p className="text-[#555] text-sm mt-0.5 leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Right: orbital diagram */}
        <motion.div
          initial={{ opacity: 0, x: 40 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.75, ease: [0.16, 1, 0.3, 1], delay: 0.12 }}
          className="flex items-center justify-center"
          aria-hidden
        >
          <div className="relative w-72 h-72 md:w-96 md:h-96">
            {/* Concentric rings */}
            {[1, 0.7, 0.4, 0.15].map((op, i) => (
              <div
                key={i}
                className="absolute inset-0 rounded-full border border-[#4ade80] animate-ring-pulse"
                style={{
                  opacity: op,
                  transform: `scale(${1 + i * 0.18})`,
                  animationDelay: `${i * 0.45}s`,
                  animationDuration: `${3.2 + i * 0.5}s`,
                }}
              />
            ))}

            {/* Centre icon */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-24 h-24 rounded-2xl bg-[rgba(74,222,128,0.07)] border border-[rgba(74,222,128,0.25)] flex items-center justify-center animate-glow-pulse">
                <Glasses size={44} className="text-[#4ade80]" />
              </div>
            </div>

            {/* Orbiting dots */}
            {[0, 60, 120, 180, 240, 300].map((deg, i) => (
              <div
                key={i}
                className="absolute w-2 h-2 rounded-full bg-[#4ade80]"
                style={{
                  top: '50%',
                  left: '50%',
                  marginTop: -4,
                  marginLeft: -4,
                  transform: `rotate(${deg}deg) translateX(130px)`,
                  opacity: 0.35 + (i % 3) * 0.2,
                }}
              />
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  )
}
