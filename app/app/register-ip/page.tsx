import Link from "next/link";
import { ConnectKitButton } from "connectkit";
import IPRegistration from "@/components/IPRegistration";

export default function RegisterIPPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg"></div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Jarvis IP
            </h1>
          </Link>
          <div className="flex items-center gap-4">
            <Link 
              href="/"
              className="text-gray-600 hover:text-blue-600 font-medium"
            >
              ← Back
            </Link>
            <ConnectKitButton />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-12">
        <div className="max-w-3xl mx-auto">
          {/* Page Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Register Your IP Asset
            </h1>
            <p className="text-lg text-gray-600">
              Upload your creative work and register it on Story Protocol blockchain
            </p>
          </div>

          {/* Important Notice */}
          <div className="mb-8 p-6 bg-yellow-50 border-2 border-yellow-200 rounded-xl">
            <div className="flex gap-3">
              <div className="text-2xl">⚠️</div>
              <div>
                <h3 className="font-bold text-yellow-900 mb-2">Before You Start</h3>
                <ul className="text-sm text-yellow-800 space-y-1 list-disc list-inside">
                  <li>Connect your wallet (MetaMask recommended)</li>
                  <li>Get testnet tokens from <a href="https://faucet.story.foundation/" target="_blank" className="underline font-semibold">Story Faucet</a></li>
                  <li>You will pay gas fees for the registration transaction</li>
                  <li>Your image will be checked for uniqueness (85% threshold)</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Registration Form */}
          <div className="bg-white rounded-2xl shadow-xl p-8 mb-12">
            <IPRegistration />
          </div>

          {/* FAQ Section */}
          <div className="bg-white rounded-2xl shadow-lg p-8">
            <h2 className="text-2xl font-bold mb-6">Frequently Asked Questions</h2>
            
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-lg mb-2">💰 How much does it cost?</h3>
                <p className="text-gray-600">
                  On testnet, it's <strong>FREE</strong>! You just need testnet tokens from the faucet. 
                  On mainnet, you'll pay gas fees (~$2-20) depending on network congestion.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-lg mb-2">🔒 What gets stored on-chain?</h3>
                <p className="text-gray-600">
                  Your image and metadata are stored on IPFS (decentralized storage). 
                  The blockchain stores the NFT ownership, IP registration, and license terms.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-lg mb-2">🎨 What file types are supported?</h3>
                <p className="text-gray-600">
                  Currently PNG, JPG, JPEG, GIF, and WebP. Maximum file size: 50MB.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-lg mb-2">⚖️ What license types can I choose?</h3>
                <p className="text-gray-600">
                  <strong>Non-commercial:</strong> Free use with attribution, no commercial use.<br/>
                  <strong>Commercial:</strong> Set revenue share % and minting fee for licensees.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-lg mb-2">❓ What if my image is similar to another?</h3>
                <p className="text-gray-600">
                  If similarity is ≥85%, registration will be rejected to prevent conflicts. 
                  You'll see details about the conflicting asset.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-lg mb-2">🔗 Can I view my registered IP?</h3>
                <p className="text-gray-600">
                  Yes! After registration, you'll get a link to Story Explorer where you can 
                  view your IP, NFT, and license terms.
                </p>
              </div>
            </div>
          </div>

          {/* Help Section */}
          <div className="mt-8 text-center p-6 bg-blue-50 rounded-xl">
            <p className="text-gray-700 mb-3">
              Need help? Check out the documentation or get testnet tokens
            </p>
            <div className="flex gap-3 justify-center flex-wrap">
              <a
                href="https://docs.story.foundation/"
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
              >
                📖 Documentation
              </a>
              <a
                href="https://faucet.story.foundation/"
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-medium"
              >
                💧 Get Testnet Tokens
              </a>
              <a
                href="https://aeneid.explorer.story.foundation/"
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 border-2 border-gray-300 rounded-lg hover:border-blue-600 hover:text-blue-600 transition-colors text-sm font-medium"
              >
                🔍 Explorer
              </a>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

