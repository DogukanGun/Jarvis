'use client'

import { motion } from 'framer-motion'
import { ChevronDown } from 'lucide-react'
import Logo from './Logo'

export default function Hero() {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center text-center overflow-hidden pt-16">
      {/* Animated dot grid */}
      <div
        className="absolute inset-0 opacity-25 animate-dot-grid"
        style={{
          backgroundImage:
            'radial-gradient(circle, rgba(74,222,128,0.5) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      {/* Radial fade — edges to near-black */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse 80% 60% at 50% 50%, transparent 0%, #0a0a0a 80%)',
        }}
      />

      <div className="relative z-10 max-w-4xl mx-auto px-6 flex flex-col items-center gap-8">
        {/* Logo with glow halo */}
        <motion.div
          initial={{ opacity: 0, scale: 0.75 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="relative"
        >
          <div
            className="absolute rounded-full animate-ring-pulse"
            style={{
              width: 140,
              height: 140,
              top: -26,
              left: -26,
              background:
                'radial-gradient(circle, rgba(74,222,128,0.18) 0%, transparent 70%)',
            }}
          />
          <Logo size={88} className="animate-glow-pulse relative z-10" />
        </motion.div>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.75, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="font-display font-bold text-5xl md:text-7xl leading-[1.05] tracking-tight text-[#f0f0f0]"
        >
          The AI agent that lives on your machine{' '}
          <span className="text-[#4ade80]">and works for you.</span>
        </motion.h1>

        {/* Sub */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.38, ease: 'easeOut' }}
          className="text-xl md:text-2xl text-[#666] max-w-2xl leading-relaxed"
        >
          Trade crypto, research anything, guard your laptop, read contracts —
          all in plain language, all offline, all yours.
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.65, delay: 0.52, ease: 'easeOut' }}
          className="flex flex-col sm:flex-row items-center gap-4"
        >
          <a
            href="#download"
            className="px-9 py-4 rounded-full bg-[#4ade80] text-[#0a0a0a] font-bold text-lg hover:bg-[#4ade80]/90 hover:shadow-[0_0_36px_rgba(74,222,128,0.4)] active:scale-95 transition-all"
          >
            Download Free
          </a>
          <a
            href="https://github.com/DogukanGun/Jarvis"
            target="_blank"
            rel="noopener noreferrer"
            className="px-9 py-4 rounded-full border border-[rgba(74,222,128,0.3)] text-[#f0f0f0] font-semibold text-lg hover:border-[#4ade80] hover:text-[#4ade80] transition-all"
          >
            View on GitHub
          </a>
        </motion.div>

        {/* Badge */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.72 }}
          className="text-xs text-[#3a3a3a] tracking-[0.18em] uppercase"
        >
          Free · Open source · No account required
        </motion.p>
      </div>

      {/* Scroll cue */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.1 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 text-[#4ade80] animate-chevron"
      >
        <ChevronDown size={26} />
      </motion.div>
    </section>
  )
}
