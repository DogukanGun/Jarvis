import type { Metadata } from 'next'
import { Inter, Space_Grotesk } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const spaceGrotesk = Space_Grotesk({ subsets: ['latin'], variable: '--font-space-grotesk' })

export const metadata: Metadata = {
  title: 'Jarvis — Your Personal AI Agent',
  description:
    'The AI agent that lives on your machine and works for you. Trade crypto, research anything, guard your laptop — all offline, all yours.',
  openGraph: {
    title: 'Jarvis — Your Personal AI Agent',
    description:
      'Trade crypto, research anything, guard your laptop. All offline, all yours.',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${spaceGrotesk.variable}`}>
      <body className="bg-[#0a0a0a] text-[#f0f0f0] font-sans antialiased">
        {children}
      </body>
    </html>
  )
}
