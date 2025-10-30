

'use client';

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Wallet, ArrowRight, Zap, Shield, Code2, Globe, DollarSign, CheckCircle2, TrendingUp, Users, Rocket } from "lucide-react";

export default function Home() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-linear-to-br from-[#0F172A] via-[#1e1b4b] to-[#0F172A]">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-[#F7931A] rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-[#6B46C1] rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse" style={{ animationDelay: '1s' }}></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-[#3B82F6] rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse" style={{ animationDelay: '2s' }}></div>
      </div>

      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSAxMCAwIEwgMCAwIDAgMTAiIGZpbGw9Im5vbmUiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS1vcGFjaXR5PSIwLjAzIiBzdHJva2Utd2lkdGg9IjEiLz48L3BhdHRlcm4+PC9kZWZzPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9InVybCgjZ3JpZCkiLz48L3N2Zz4=')] opacity-30"></div>

      <div className="relative container mx-auto px-4 sm:px-6 lg:px-8">
        {/* Navigation */}
        <nav className="flex items-center justify-between py-6 animate-appear">
          <div className="flex items-center gap-3">
            <div className="relative w-10 h-10 bg-linear-to-br from-[#F7931A] to-[#FCD34D] rounded-lg flex items-center justify-center shadow-lg shadow-[#F7931A]/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="text-2xl font-bold text-white tracking-tight">JARVIS</span>
          </div>
          <Button 
            variant="outline" 
            className="border-white/20 bg-transparent text-white hover:bg-white/10 hover:text-white hover:border-white/30 backdrop-blur-sm inline-flex items-center gap-2"
          >
            <Wallet className="w-4 h-4" />
            <span>Connect Wallet</span>
          </Button>
        </nav>

        {/* Hero Content */}
        <div className="flex flex-col items-center text-center pt-20 pb-32 space-y-8">
          {/* Badge */}
          <Badge 
            variant="secondary" 
            className="bg-white/10 text-white border-white/20 backdrop-blur-md px-6 py-2 text-sm font-medium hover:bg-white/15 transition-all animate-appear-zoom inline-flex items-center gap-2"
            style={{ animationDelay: '0.1s' }}
          >
            <Zap className="w-4 h-4 text-[#FCD34D]" />
            <span>Powered by Mezo × Bitcoin L2</span>
          </Badge>

          {/* Main Heading */}
          <h1 
            className="text-6xl sm:text-7xl lg:text-8xl font-bold text-white max-w-5xl leading-tight tracking-tight animate-appear-zoom"
            style={{ animationDelay: '0.2s' }}
          >
            AI for the other{' '}
            <span className="bg-linear-to-r from-[#F7931A] via-[#FCD34D] to-[#F97316] bg-clip-text text-transparent">
              3.4 billion
            </span>
          </h1>

          {/* Subheading */}
          <p 
            className="text-xl sm:text-2xl text-white/80 max-w-3xl leading-relaxed animate-appear"
            style={{ animationDelay: '0.3s' }}
          >
            The first pay-per-use AI platform built on Bitcoin L2.
            <br />
            <span className="text-white/60">No credit card. No subscription. Just crypto.</span>
          </p>

          {/* CTA Buttons */}
          <div 
            className="flex flex-col sm:flex-row gap-4 pt-4 animate-appear"
            style={{ animationDelay: '0.4s' }}
          >
            <Button 
              size="lg"
              className="bg-linear-to-r from-[#F7931A] to-[#F97316] hover:from-[#FCD34D] hover:to-[#F7931A] text-white font-bold text-lg px-8 py-6 shadow-2xl shadow-[#F7931A]/30 hover:shadow-[#F7931A]/50 transition-all hover:scale-105 h-auto inline-flex items-center gap-2 border-0"
            >
              <span>Get Started</span>
              <ArrowRight className="w-5 h-5" />
            </Button>
            <Button 
              size="lg"
              variant="outline"
              className="border-2 border-white/30 bg-transparent text-white hover:bg-white/10 hover:border-white/40 font-semibold text-lg px-8 py-6 backdrop-blur-sm h-auto"
            >
              View Demo
            </Button>
          </div>

          {/* Stats */}
          <div 
            className="flex flex-wrap justify-center gap-8 pt-8 text-sm animate-appear"
            style={{ animationDelay: '0.5s' }}
          >
            <div className="text-white/70">
              💎 Starting at <span className="font-bold text-[#FCD34D]">0.001 MEZO</span> per query
            </div>
            <div className="text-white/70">
              ⚡ <span className="font-bold text-[#10B981]">99.9% cheaper</span> gas than Ethereum
            </div>
            <div className="text-white/70">
              🌍 <span className="font-bold text-[#3B82F6]">420M</span> potential users
            </div>
          </div>

          {/* Feature Pills */}
          <div 
            className="flex flex-wrap justify-center gap-3 pt-8 max-w-3xl animate-appear"
            style={{ animationDelay: '0.6s' }}
          >
            <FeaturePill icon={<Shield />} text="Secure & Private" />
            <FeaturePill icon={<Code2 />} text="Code Execution" />
            <FeaturePill icon={<Globe />} text="Global Access" />
            <FeaturePill icon={<Zap />} text="Instant Payments" />
          </div>
        </div>

        {/* Floating Card Preview */}
        <div 
          className="relative max-w-5xl mx-auto -mt-20 mb-20 animate-appear-zoom"
          style={{ animationDelay: '0.7s' }}
        >
          <div className="absolute inset-0 bg-linear-to-r from-[#F7931A] via-[#6B46C1] to-[#3B82F6] rounded-3xl blur-2xl opacity-20"></div>
          <div className="relative bg-white/5 backdrop-blur-xl border border-white/20 rounded-3xl p-8 shadow-2xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span className="ml-4 text-white/60 text-sm font-mono">jarvis-terminal</span>
            </div>
            <div className="space-y-3 font-mono text-sm">
              <div className="flex items-start gap-3">
                <span className="text-[#F7931A]">$</span>
                <span className="text-white/90">jarvis ask &quot;Create a liquidity pool contract on Mezo&quot;</span>
              </div>
              <div className="flex items-start gap-3 text-[#10B981]">
                <span>✓</span>
                <span>Generated 250 lines of Solidity code</span>
              </div>
              <div className="flex items-start gap-3 text-[#10B981]">
                <span>✓</span>
                <span>Deployed to Mezo testnet at 0x742d35Cc...</span>
              </div>
              <div className="flex items-start gap-3 text-[#3B82F6]">
                <span>ℹ</span>
                <span>Cost: 0.01 MEZO ($0.10) • Balance: 9.99 MEZO</span>
              </div>
            </div>
          </div>
        </div>

        {/* Problem/Solution Section */}
        <div className="max-w-6xl mx-auto py-20">
          <div className="text-center mb-16">
            <h2 className="text-4xl sm:text-5xl font-bold text-white mb-4">
              The AI Access Problem
            </h2>
            <p className="text-xl text-white/60 max-w-2xl mx-auto">
              Billions are locked out of the AI revolution by payment barriers
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8 mb-20">
            {/* Problem Card */}
            <div className="relative group">
              <div className="absolute inset-0 bg-linear-to-br from-red-500/20 to-orange-500/20 rounded-3xl blur-xl opacity-50 group-hover:opacity-70 transition-opacity"></div>
              <div className="relative bg-white/5 backdrop-blur-md border border-red-500/20 rounded-3xl p-8 h-full">
                <div className="inline-flex items-center justify-center w-12 h-12 bg-red-500/20 rounded-xl mb-6">
                  <span className="text-3xl">❌</span>
                </div>
                <h3 className="text-2xl font-bold text-white mb-6">Today&apos;s Reality</h3>
                <ul className="space-y-4">
                  <ProblemItem text="3.4 billion people lack credit cards" />
                  <ProblemItem text="AI APIs require $20/month subscriptions" />
                  <ProblemItem text="Emerging markets shut out completely" />
                  <ProblemItem text="Bitcoin sits idle with no utility" />
                  <ProblemItem text="High gas fees make micro-payments impossible" />
                </ul>
              </div>
            </div>

            {/* Solution Card */}
            <div className="relative group">
              <div className="absolute inset-0 bg-linear-to-br from-green-500/20 to-blue-500/20 rounded-3xl blur-xl opacity-50 group-hover:opacity-70 transition-opacity"></div>
              <div className="relative bg-white/5 backdrop-blur-md border border-green-500/20 rounded-3xl p-8 h-full">
                <div className="inline-flex items-center justify-center w-12 h-12 bg-green-500/20 rounded-xl mb-6">
                  <span className="text-3xl">✅</span>
                </div>
                <h3 className="text-2xl font-bold text-white mb-6">Jarvis Solution</h3>
                <ul className="space-y-4">
                  <SolutionItem text="Pay with Bitcoin on Mezo L2" />
                  <SolutionItem text="Micro-payments starting at $0.001" />
                  <SolutionItem text="No KYC, no barriers, truly global" />
                  <SolutionItem text="Give Bitcoin real productive utility" />
                  <SolutionItem text="99.9% cheaper gas than Ethereum L1" />
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="max-w-7xl mx-auto py-20">
          <div className="text-center mb-16">
            <Badge 
              variant="secondary" 
              className="bg-[#F7931A]/10 text-[#FCD34D] border-[#F7931A]/20 backdrop-blur-md px-6 py-2 text-sm font-medium mb-6 inline-flex items-center gap-2"
            >
              <Sparkles className="w-4 h-4" />
              <span>Powerful Capabilities</span>
            </Badge>
            <h2 className="text-4xl sm:text-5xl font-bold text-white mb-4">
              Built for Bitcoin Developers
            </h2>
            <p className="text-xl text-white/60 max-w-2xl mx-auto">
              Your personal AI agent with tools designed for the Mezo ecosystem
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <FeatureCard
              icon="🤖"
              title="Smart Contract Assistant"
              description="Generate, audit, and deploy Mezo contracts using natural language. Get instant code reviews and security suggestions."
              gradient="from-purple-500/20 to-pink-500/20"
            />
            <FeatureCard
              icon="⚡"
              title="Code Execution Sandbox"
              description="Run Python, Go, JavaScript in isolated Docker containers. Test your Bitcoin scripts safely before deployment."
              gradient="from-yellow-500/20 to-orange-500/20"
            />
            <FeatureCard
              icon="📊"
              title="DeFi Analytics"
              description="Monitor gas prices, yields, and liquidity across Mezo protocols in real-time. Make data-driven decisions."
              gradient="from-blue-500/20 to-cyan-500/20"
            />
            <FeatureCard
              icon="🧠"
              title="Persistent Memory"
              description="Your agent remembers your coding style, preferences, and project context using Neo4j knowledge graphs."
              gradient="from-green-500/20 to-emerald-500/20"
            />
            <FeatureCard
              icon="🔐"
              title="Security First"
              description="Every user gets an isolated container. Your code, your data, your control. Enterprise-grade security."
              gradient="from-red-500/20 to-rose-500/20"
            />
            <FeatureCard
              icon="🌐"
              title="Multi-Interface Access"
              description="Use Jarvis via CLI, Web UI, or API. Integrate into your existing workflow seamlessly."
              gradient="from-indigo-500/20 to-violet-500/20"
            />
          </div>
        </div>

        {/* Why Mezo Section */}
        <div className="max-w-6xl mx-auto py-20">
          <div className="relative">
            <div className="absolute inset-0 bg-linear-to-r from-[#F7931A] via-[#FCD34D] to-[#F97316] rounded-3xl blur-2xl opacity-20"></div>
            <div className="relative bg-linear-to-br from-[#F7931A]/10 to-[#F97316]/10 backdrop-blur-md border border-[#F7931A]/20 rounded-3xl p-12">
              <div className="text-center mb-12">
                <h2 className="text-4xl sm:text-5xl font-bold text-white mb-4">
                  Why Build on Mezo?
                </h2>
                <p className="text-xl text-white/80 max-w-2xl mx-auto">
                  Mezo&apos;s Bitcoin L2 makes the impossible possible
                </p>
              </div>

              <div className="grid md:grid-cols-3 gap-8">
                <div className="text-center">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-[#F7931A]/20 rounded-2xl mb-4">
                    <Zap className="w-8 h-8 text-[#FCD34D]" />
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-3">Lightning Fast</h3>
                  <p className="text-white/70 leading-relaxed">
                    Sub-2 second finality makes AI interactions feel instant. No waiting, just results.
                  </p>
                </div>

                <div className="text-center">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-[#F7931A]/20 rounded-2xl mb-4">
                    <DollarSign className="w-8 h-8 text-[#FCD34D]" />
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-3">Dirt Cheap</h3>
                  <p className="text-white/70 leading-relaxed">
                    Micro-payments only viable on L2. $0.001 transactions impossible on Bitcoin L1.
                  </p>
                </div>

                <div className="text-center">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-[#F7931A]/20 rounded-2xl mb-4">
                    <Shield className="w-8 h-8 text-[#FCD34D]" />
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-3">Bitcoin Security</h3>
                  <p className="text-white/70 leading-relaxed">
                    Inherit Bitcoin&apos;s legendary security with L2 scalability. Best of both worlds.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Pricing Section */}
        <div className="max-w-6xl mx-auto py-20">
          <div className="text-center mb-16">
            <Badge 
              variant="secondary" 
              className="bg-[#10B981]/10 text-[#10B981] border-[#10B981]/20 backdrop-blur-md px-6 py-2 text-sm font-medium mb-6 inline-flex items-center gap-2"
            >
              <DollarSign className="w-4 h-4" />
              <span>Transparent Pricing</span>
            </Badge>
            <h2 className="text-4xl sm:text-5xl font-bold text-white mb-4">
              Simple, Fair Pricing
            </h2>
            <p className="text-xl text-white/60 max-w-2xl mx-auto">
              Pay only for what you use. All transactions settled instantly on Mezo L2.
            </p>
          </div>

          <div className="grid md:grid-cols-4 gap-6 mb-12">
            <PricingCard
              operation="AI Query"
              cost="0.001 MEZO"
              description="Ask questions, get answers"
              comparison="vs $0.10 on OpenAI"
            />
            <PricingCard
              operation="Code Execution"
              cost="0.01 MEZO"
              description="Run scripts, test code"
              comparison="vs $1.00 traditional"
            />
            <PricingCard
              operation="Contract Deploy"
              cost="0.05 MEZO"
              description="Deploy to Mezo testnet"
              comparison="vs $500 on ETH L1"
            />
            <PricingCard
              operation="File Operations"
              cost="0.0001 MEZO"
              description="Read/write files"
              comparison="Free tier included"
            />
          </div>

          <div className="bg-white/5 backdrop-blur-md border border-[#FCD34D]/20 rounded-2xl p-8">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="flex-1">
                <h3 className="text-2xl font-bold text-white mb-2">Bulk Discounts Available</h3>
                <p className="text-white/70">
                  Power users get up to 30% off. Deposit 100+ MEZO tokens for premium rates.
                </p>
              </div>
              <Button 
                size="lg"
                className="bg-[#FCD34D] hover:bg-[#F7931A] text-[#0F172A] font-bold px-8 shrink-0"
              >
                View Pricing Details
              </Button>
            </div>
          </div>
        </div>

        {/* How It Works Section */}
        <div className="max-w-6xl mx-auto py-20">
          <div className="text-center mb-16">
            <h2 className="text-4xl sm:text-5xl font-bold text-white mb-4">
              How It Works
            </h2>
            <p className="text-xl text-white/60 max-w-2xl mx-auto">
              Get started in less than 60 seconds
            </p>
          </div>

          <div className="space-y-8">
            <StepCard
              number="1"
              title="Connect Your Wallet"
              description="Use MetaMask, WalletConnect, or any Mezo-compatible wallet. No registration, no KYC required."
              icon={<Wallet className="w-6 h-6" />}
            />
            <StepCard
              number="2"
              title="Deposit Tokens"
              description="Add MEZO tokens or bridge tBTC to your account. Start with as little as $1 worth of tokens."
              icon={<DollarSign className="w-6 h-6" />}
            />
            <StepCard
              number="3"
              title="Get Your Personal Agent"
              description="We automatically spin up an isolated Docker container with your AI agent. Full privacy, full control."
              icon={<Rocket className="w-6 h-6" />}
            />
            <StepCard
              number="4"
              title="Start Building"
              description="Chat via web, CLI, or API. Every interaction is micro-charged in real-time. Withdraw unused funds anytime."
              icon={<Code2 className="w-6 h-6" />}
            />
          </div>
        </div>

        {/* Social Proof / Stats Section */}
        <div className="max-w-6xl mx-auto py-20">
          <div className="bg-linear-to-br from-[#6B46C1]/10 to-[#3B82F6]/10 backdrop-blur-md border border-[#6B46C1]/20 rounded-3xl p-12">
            <div className="text-center mb-12">
              <h2 className="text-4xl sm:text-5xl font-bold text-white mb-4">
                Built for Scale
              </h2>
              <p className="text-xl text-white/70">
                Infrastructure ready for millions of users
              </p>
            </div>

            <div className="grid md:grid-cols-4 gap-8">
              <StatCard
                icon={<Users className="w-8 h-8 text-[#3B82F6]" />}
                number="420M"
                label="Potential Users"
                sublabel="Global crypto holders"
              />
              <StatCard
                icon={<Zap className="w-8 h-8 text-[#FCD34D]" />}
                number="<2s"
                label="Transaction Time"
                sublabel="Instant settlement"
              />
              <StatCard
                icon={<TrendingUp className="w-8 h-8 text-[#10B981]" />}
                number="99.9%"
                label="Cost Savings"
                sublabel="vs Ethereum L1"
              />
              <StatCard
                icon={<Shield className="w-8 h-8 text-[#F97316]" />}
                number="100%"
                label="Isolation"
                sublabel="Per-user containers"
              />
            </div>
          </div>
        </div>

        {/* Final CTA Section */}
        <div className="max-w-6xl mx-auto py-20">
          <div className="relative">
            <div className="absolute inset-0 bg-linear-to-r from-[#F7931A] via-[#6B46C1] to-[#3B82F6] rounded-3xl blur-3xl opacity-30"></div>
            <div className="relative bg-white/5 backdrop-blur-xl border border-white/20 rounded-3xl p-16 text-center">
              <div className="inline-flex items-center justify-center w-20 h-20 bg-linear-to-br from-[#F7931A] to-[#FCD34D] rounded-2xl mb-8 mx-auto">
                <Sparkles className="w-10 h-10 text-white" />
              </div>
              
              <h2 className="text-5xl sm:text-6xl font-bold text-white mb-6">
                Give Bitcoin Real Utility
              </h2>
              
              <p className="text-2xl text-white/80 mb-8 max-w-3xl mx-auto">
                Join the movement to democratize AI access with Bitcoin L2
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
                <Button 
                  size="lg"
                  className="bg-linear-to-r from-[#F7931A] to-[#F97316] hover:from-[#FCD34D] hover:to-[#F7931A] text-white font-bold text-xl px-12 py-8 shadow-2xl shadow-[#F7931A]/30 hover:shadow-[#F7931A]/50 transition-all hover:scale-105 h-auto inline-flex items-center gap-3 border-0"
                >
                  <Wallet className="w-6 h-6" />
                  <span>Connect Wallet & Start</span>
                </Button>
                <Button 
                  size="lg"
                  variant="outline"
                  className="border-2 border-white/30 bg-transparent text-white hover:bg-white/10 hover:border-white/40 font-semibold text-xl px-12 py-8 backdrop-blur-sm h-auto"
                >
                  Read Documentation
                </Button>
              </div>

              <div className="flex flex-wrap justify-center gap-8 text-white/60 text-sm">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#10B981]" />
                  <span>No credit card required</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#10B981]" />
                  <span>Withdraw funds anytime</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#10B981]" />
                  <span>Open source on GitHub</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="border-t border-white/10 py-12 mt-20">
          <div className="max-w-6xl mx-auto">
            <div className="flex flex-col md:flex-row justify-between items-center gap-6">
              <div className="flex items-center gap-3">
                <div className="relative w-10 h-10 bg-linear-to-br from-[#F7931A] to-[#FCD34D] rounded-lg flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                  <div className="text-xl font-bold text-white">JARVIS</div>
                  <div className="text-sm text-white/60">AI for Everyone</div>
                </div>
              </div>

              <div className="flex gap-8 text-white/70">
                <a href="#" className="hover:text-white transition-colors">Documentation</a>
                <a href="#" className="hover:text-white transition-colors">GitHub</a>
                <a href="#" className="hover:text-white transition-colors">Discord</a>
                <a href="#" className="hover:text-white transition-colors">Twitter</a>
              </div>

              <div className="text-white/60 text-sm">
                Built for Mezo Hackathon 2025
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}

function FeaturePill({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="inline-flex items-center gap-2 bg-white/5 backdrop-blur-sm border border-white/10 rounded-full px-4 py-2 text-white/80 hover:bg-white/10 hover:border-white/20 transition-all cursor-default">
      <div className="w-4 h-4 text-[#FCD34D] flex items-center justify-center">{icon}</div>
      <span className="text-sm font-medium">{text}</span>
    </div>
  );
}

function ProblemItem({ text }: { text: string }) {
  return (
    <li className="flex items-start gap-3 text-white/80">
      <span className="text-red-400 mt-1 shrink-0">✗</span>
      <span className="leading-relaxed">{text}</span>
    </li>
  );
}

function SolutionItem({ text }: { text: string }) {
  return (
    <li className="flex items-start gap-3 text-white/80">
      <span className="text-green-400 mt-1 shrink-0">✓</span>
      <span className="leading-relaxed">{text}</span>
    </li>
  );
}

function FeatureCard({ icon, title, description, gradient }: { 
  icon: string; 
  title: string; 
  description: string; 
  gradient: string;
}) {
  return (
    <div className="relative group">
      <div className={`absolute inset-0 bg-linear-to-br ${gradient} rounded-2xl blur-xl opacity-0 group-hover:opacity-50 transition-opacity duration-300`}></div>
      <div className="relative bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl p-6 h-full hover:border-white/20 transition-all duration-300">
        <div className="text-4xl mb-4">{icon}</div>
        <h3 className="text-xl font-bold text-white mb-3">{title}</h3>
        <p className="text-white/70 leading-relaxed">{description}</p>
      </div>
    </div>
  );
}

function PricingCard({ operation, cost, description, comparison }: {
  operation: string;
  cost: string;
  description: string;
  comparison: string;
}) {
  return (
    <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl p-6 hover:border-[#FCD34D]/30 transition-all">
      <div className="text-4xl font-bold text-[#FCD34D] mb-2">{cost}</div>
      <div className="text-xl font-semibold text-white mb-2">{operation}</div>
      <div className="text-white/70 text-sm mb-3">{description}</div>
      <div className="text-xs text-[#10B981] font-medium">{comparison}</div>
    </div>
  );
}

function StepCard({ number, title, description, icon }: {
  number: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="relative">
      <div className="flex items-start gap-6 bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl p-8 hover:border-white/20 transition-all">
        <div className="shrink-0 w-16 h-16 bg-linear-to-br from-[#F7931A] to-[#FCD34D] rounded-2xl flex items-center justify-center text-3xl font-bold text-white shadow-lg shadow-[#F7931A]/20">
          {number}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-3">
            <div className="text-[#FCD34D]">{icon}</div>
            <h3 className="text-2xl font-bold text-white">{title}</h3>
          </div>
          <p className="text-white/70 leading-relaxed">{description}</p>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, number, label, sublabel }: {
  icon: React.ReactNode;
  number: string;
  label: string;
  sublabel: string;
}) {
  return (
    <div className="text-center">
      <div className="inline-flex items-center justify-center w-16 h-16 bg-white/10 rounded-2xl mb-4">
        {icon}
      </div>
      <div className="text-4xl font-bold text-white mb-2">{number}</div>
      <div className="text-lg font-semibold text-white mb-1">{label}</div>
      <div className="text-sm text-white/60">{sublabel}</div>
    </div>
  );
}
