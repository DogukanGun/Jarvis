import type { Metadata } from 'next';
import { Geist_Mono } from 'next/font/google';
import './globals.css';

const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Jarvis Chat',
  description: 'Chat interface for the Jarvis AI assistant',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistMono.variable} dark`}>
      <body className="antialiased min-h-screen bg-slate-950 text-slate-100 font-mono">
        {children}
      </body>
    </html>
  );
}
