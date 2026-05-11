'use client'

import { useEffect, useState } from 'react'
import Logo from './Logo'

export default function Nav() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-[#0a0a0a]/80 backdrop-blur-md border-b border-[rgba(74,222,128,0.1)]'
          : ''
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Logo size={28} />
          <span className="font-display font-bold text-sm tracking-[0.22em] uppercase text-[#f0f0f0]">
            Jarvis
          </span>
        </div>

        <div className="flex items-center gap-5">
          <a
            href="https://github.com/DogukanGun/Jarvis"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:block text-sm text-[#555] hover:text-[#f0f0f0] transition-colors"
          >
            GitHub
          </a>
          <a
            href="#download"
            className="px-5 py-2 rounded-full bg-[#4ade80] text-[#0a0a0a] text-sm font-bold hover:bg-[#4ade80]/90 hover:shadow-[0_0_20px_rgba(74,222,128,0.3)] transition-all"
          >
            Download
          </a>
        </div>
      </div>
    </nav>
  )
}
