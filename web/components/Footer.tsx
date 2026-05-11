import Logo from './Logo'
import { Github } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="border-t border-[rgba(74,222,128,0.07)] py-12 px-6">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">

        <div className="flex flex-col items-center md:items-start gap-2">
          <div className="flex items-center gap-3">
            <Logo size={22} />
            <span className="font-display font-bold text-sm tracking-[0.22em] uppercase text-[#f0f0f0]">
              Jarvis
            </span>
          </div>
          <p className="text-xs text-[#333]">© 2026 Jarvis. Open source.</p>
        </div>

        <p className="text-xs text-[#333] text-center max-w-xs">
          Built for people who want AI that works for them, not the other way around.
        </p>

        <a
          href="https://github.com/DogukanGun/Jarvis"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-sm text-[#444] hover:text-[#4ade80] transition-colors"
        >
          <Github size={15} />
          GitHub
        </a>
      </div>
    </footer>
  )
}
