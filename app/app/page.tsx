import Link from "next/link";
import Image from "next/image";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg"></div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Jarvis IP
            </h1>
          </div>
          <nav className="flex gap-4">
            <Link 
              href="/register-ip"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Register IP
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <main className="container mx-auto px-4 py-20">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-block mb-6 px-4 py-2 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
            🔒 Powered by Story Protocol
          </div>
          
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
            Protect Your Intellectual Property
          </h1>
          
          <p className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto">
            AI-powered similarity detection + blockchain registration. 
            Secure your creative work on Story Protocol with just a few clicks.
          </p>

          <div className="flex gap-4 justify-center">
            <Link
              href="/register-ip"
              className="px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl font-semibold hover:shadow-xl transition-all text-lg"
            >
              🚀 Register Your IP
            </Link>
            <a
              href="https://docs.story.foundation/"
              target="_blank"
              rel="noopener noreferrer"
              className="px-8 py-4 border-2 border-gray-300 rounded-xl font-semibold hover:border-blue-600 hover:text-blue-600 transition-all text-lg"
            >
              📖 Learn More
            </a>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-3 gap-8 mt-20 max-w-5xl mx-auto">
          <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow">
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">🤖</span>
            </div>
            <h3 className="text-xl font-bold mb-3">AI-Powered Detection</h3>
            <p className="text-gray-600">
              Advanced image embeddings check uniqueness with 85% similarity threshold. 
              Your work is protected from copies.
            </p>
          </div>

          <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow">
            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">⛓️</span>
            </div>
            <h3 className="text-xl font-bold mb-3">Blockchain Registry</h3>
            <p className="text-gray-600">
              Register as NFT on Story Protocol. Immutable, transparent, 
              and globally recognized ownership.
            </p>
          </div>

          <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow">
            <div className="w-12 h-12 bg-pink-100 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">💰</span>
            </div>
            <h3 className="text-xl font-bold mb-3">License & Earn</h3>
            <p className="text-gray-600">
              Set commercial terms with revenue sharing. 
              Automatically earn from licenses minted by others.
            </p>
          </div>
        </div>

        {/* How It Works */}
        <div className="mt-24 max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
          
          <div className="space-y-6">
            <div className="flex gap-6 items-start bg-white rounded-xl p-6 shadow-md">
              <div className="flex-shrink-0 w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">
                1
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-2">Upload Your Work</h3>
                <p className="text-gray-600">
                  Upload your image or artwork. Our AI analyzes it and generates a unique fingerprint.
                </p>
              </div>
            </div>

            <div className="flex gap-6 items-start bg-white rounded-xl p-6 shadow-md">
              <div className="flex-shrink-0 w-10 h-10 bg-purple-600 text-white rounded-full flex items-center justify-center font-bold">
                2
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-2">Check Uniqueness</h3>
                <p className="text-gray-600">
                  Our Visual Analyser searches 768-dimensional vectors in PostgreSQL to ensure your work is unique.
                </p>
              </div>
            </div>

            <div className="flex gap-6 items-start bg-white rounded-xl p-6 shadow-md">
              <div className="flex-shrink-0 w-10 h-10 bg-pink-600 text-white rounded-full flex items-center justify-center font-bold">
                3
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-2">Set License Terms</h3>
                <p className="text-gray-600">
                  Choose commercial or non-commercial license. Set revenue share percentage and minting fees.
                </p>
              </div>
            </div>

            <div className="flex gap-6 items-start bg-white rounded-xl p-6 shadow-md">
              <div className="flex-shrink-0 w-10 h-10 bg-green-600 text-white rounded-full flex items-center justify-center font-bold">
                4
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-2">Register on Blockchain</h3>
                <p className="text-gray-600">
                  Connect your wallet, sign the transaction, and your IP is registered as an NFT on Story Protocol!
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="mt-24 text-center bg-gradient-to-r from-blue-600 to-purple-600 rounded-3xl p-12 text-white">
          <h2 className="text-3xl font-bold mb-4">Ready to Protect Your IP?</h2>
          <p className="text-xl mb-8 opacity-90">
            Join creators worldwide securing their work on Story Protocol
          </p>
          <Link
            href="/register-ip"
            className="inline-block px-10 py-4 bg-white text-blue-600 rounded-xl font-bold hover:shadow-2xl transition-all text-lg"
          >
            Get Started Now →
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t mt-20 py-12 bg-white/50">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <div>
              <h3 className="font-bold mb-4">Jarvis IP</h3>
              <p className="text-gray-600 text-sm">
                AI-powered IP protection using Story Protocol blockchain technology.
              </p>
            </div>
            <div>
              <h3 className="font-bold mb-4">Resources</h3>
              <ul className="space-y-2 text-sm">
                <li>
                  <a href="https://docs.story.foundation/" className="text-gray-600 hover:text-blue-600">
                    Story Protocol Docs
                  </a>
                </li>
                <li>
                  <a href="https://aeneid.explorer.story.foundation/" className="text-gray-600 hover:text-blue-600">
                    Block Explorer
                  </a>
                </li>
                <li>
                  <a href="https://faucet.story.foundation/" className="text-gray-600 hover:text-blue-600">
                    Get Testnet Tokens
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="font-bold mb-4">Status</h3>
              <div className="flex items-center gap-2 text-sm">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-gray-600">All services operational</span>
              </div>
            </div>
          </div>
          <div className="text-center mt-8 pt-8 border-t text-sm text-gray-600">
            <p>© 2024 Jarvis IP. Powered by Story Protocol.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
