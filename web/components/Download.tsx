'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Monitor, Terminal, Apple } from 'lucide-react'

const BASE = 'https://github.com/DogukanGun/Jarvis/releases/latest/download'

const platforms = [
  {
    id: 'mac',
    label: 'macOS',
    icon: Apple,
    description: 'macOS 12 Monterey or later',
    downloads: [{ label: 'Download .dmg', url: `${BASE}/Jarvis-1.0.0.dmg` }],
    detect: (ua: string) => /mac/i.test(ua) && !/iphone|ipad/i.test(ua),
  },
  {
    id: 'windows',
    label: 'Windows',
    icon: Monitor,
    description: 'Windows 10 / 11 (64-bit)',
    downloads: [{ label: 'Download .exe', url: `${BASE}/Jarvis-1.0.0-setup.exe` }],
    detect: (ua: string) => /win/i.test(ua),
  },
  {
    id: 'linux',
    label: 'Linux',
    icon: Terminal,
    description: 'Ubuntu, Debian, and compatible',
    downloads: [
      { label: 'Download .AppImage', url: `${BASE}/Jarvis-1.0.0.AppImage` },
      { label: 'Download .deb', url: `${BASE}/Jarvis-1.0.0.deb` },
    ],
    detect: (ua: string) => /linux/i.test(ua),
  },
]

export default function Download() {
  const [detected, setDetected] = useState<string>('mac')

  useEffect(() => {
    const ua = navigator.userAgent
    const found = platforms.find((p) => p.detect(ua))
    if (found) setDetected(found.id)
  }, [])

  return (
    <section
      id="download"
      className="py-32 px-6 border-t border-[rgba(74,222,128,0.07)]"
    >
      <div className="max-w-6xl mx-auto flex flex-col items-center gap-12">

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          <p className="text-xs text-[#4ade80] tracking-[0.2em] uppercase font-medium mb-4">
            Download
          </p>
          <h2 className="font-display font-bold text-4xl md:text-5xl text-[#f0f0f0] mb-3">
            Available on every platform
          </h2>
          <p className="text-[#555]">Free. Open source. No account required.</p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-6 w-full">
          {platforms.map(({ id, label, icon: Icon, description, downloads }, i) => {
            const active = detected === id
            return (
              <motion.div
                key={id}
                initial={{ opacity: 0, y: 32 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.55, delay: i * 0.1 }}
                className={`relative rounded-2xl border p-8 flex flex-col gap-7 transition-all ${
                  active
                    ? 'border-[rgba(74,222,128,0.5)] bg-[rgba(74,222,128,0.055)] shadow-[0_0_40px_rgba(74,222,128,0.08)]'
                    : 'border-[rgba(74,222,128,0.1)] bg-[rgba(74,222,128,0.02)]'
                }`}
              >
                {active && (
                  <div className="absolute top-4 right-4 px-2.5 py-0.5 rounded-full bg-[#4ade80] text-[#0a0a0a] text-[9px] font-bold tracking-wider uppercase">
                    Recommended
                  </div>
                )}

                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-[rgba(74,222,128,0.08)] border border-[rgba(74,222,128,0.18)] flex items-center justify-center flex-shrink-0">
                    <Icon size={22} className="text-[#4ade80]" />
                  </div>
                  <div>
                    <p className="font-display font-bold text-lg text-[#f0f0f0]">{label}</p>
                    <p className="text-xs text-[#4a4a4a] mt-0.5">{description}</p>
                  </div>
                </div>

                <div className="flex flex-col gap-3">
                  {downloads.map(({ label: dlLabel, url }) => (
                    <a
                      key={dlLabel}
                      href={url}
                      className={`w-full py-3 px-4 rounded-xl text-sm font-semibold text-center transition-all ${
                        active
                          ? 'bg-[#4ade80] text-[#0a0a0a] hover:bg-[#4ade80]/90 hover:shadow-[0_0_24px_rgba(74,222,128,0.35)]'
                          : 'border border-[rgba(74,222,128,0.2)] text-[#888] hover:border-[rgba(74,222,128,0.4)] hover:text-[#f0f0f0]'
                      }`}
                    >
                      {dlLabel}
                    </a>
                  ))}
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
