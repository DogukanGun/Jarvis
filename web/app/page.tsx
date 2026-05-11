import Nav from '@/components/Nav'
import Hero from '@/components/Hero'
import Vision from '@/components/Vision'
import Features from '@/components/Features'
import HowItWorks from '@/components/HowItWorks'
import OpenSource from '@/components/OpenSource'
import Download from '@/components/Download'
import Footer from '@/components/Footer'

export default function Home() {
  return (
    <main>
      <Nav />
      <Hero />
      <Vision />
      <Features />
      <HowItWorks />
      <OpenSource />
      <Download />
      <Footer />
    </main>
  )
}
