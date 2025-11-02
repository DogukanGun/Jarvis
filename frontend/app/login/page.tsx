'use client';

import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Sparkles, CheckCircle2 } from 'lucide-react';
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAccount, useSignMessage, useDisconnect } from 'wagmi';
import { ConnectButton } from '@rainbow-me/rainbowkit';
import { apiClient } from "@/lib/api-client";
import { toast } from "sonner";

export default function LoginPage() {
  const router = useRouter();
  const { address, isConnected } = useAccount();
  const { signMessageAsync } = useSignMessage();
  const { disconnect } = useDisconnect();
  
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!address) {
      toast.error('Please connect your wallet first');
      return;
    }
    
    setIsLoading(true);
    
    try {
      // Create message to sign
      const message = `Sign this message to authenticate with Jarvis AI.\n\nWallet: ${address}\nTimestamp: ${Date.now()}`;
      
      // Request signature from wallet
      const signature = await signMessageAsync({ message });
      
      // Call backend API with wallet auth
      const response = await apiClient.auth.walletAuth({
        wallet_address: address,
        signature,
        message,
      });
      
      // Save token and user data
      if (typeof window !== 'undefined') {
        localStorage.setItem('auth-token', response.token);
        localStorage.setItem('user', JSON.stringify(response));
      }
      
      // Show success toast
      toast.success('Login successful!', {
        description: 'Welcome back to Jarvis',
      });
      
      // Redirect to dashboard after 1 second
      setTimeout(() => {
        router.push('/dashboard');
      }, 1000);
    } catch (err) {
      console.error('Login error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Wallet authentication failed. Please try again.';
      toast.error('Authentication failed', {
        description: errorMessage,
      });
      setIsLoading(false);
    }
  };

  const handleDisconnect = () => {
    disconnect();
  };

  return (
    <div className="min-h-screen bg-[#0F172A] flex items-center justify-center p-4">
      {/* Background Effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -right-1/2 w-full h-full bg-[#F7931A]/5 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-1/2 -left-1/2 w-full h-full bg-[#6B46C1]/5 rounded-full blur-3xl"></div>
      </div>

      <div className="relative w-full max-w-md">
        {/* Logo Section */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-linear-to-br from-[#F7931A] to-[#FCD34D] rounded-2xl mb-4">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Welcome back</h1>
          <p className="text-white/60">Connect your wallet to sign in</p>
        </div>

        {/* Login Card */}
        <div className="bg-[#1e1b4b]/50 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl">
          {/* Step 1: Connect Wallet */}
          {!isConnected && (
            <div className="space-y-6">
              <div className="text-center space-y-4">
                <div className="w-20 h-20 mx-auto bg-white/5 rounded-full flex items-center justify-center mb-4">
                  <svg className="w-10 h-10 text-[#F7931A]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-white">Connect Your Wallet</h3>
                <p className="text-white/60 text-sm">
                  Sign in securely using your Web3 wallet. No password needed.
                </p>
              </div>

              <div className="flex justify-center">
                <ConnectButton />
              </div>

              <div className="space-y-3 pt-4">
                <div className="flex items-center gap-3 text-white/60 text-sm">
                  <CheckCircle2 className="w-5 h-5 text-green-400 shrink-0" />
                  <span>Secure wallet-based authentication</span>
                </div>
                <div className="flex items-center gap-3 text-white/60 text-sm">
                  <CheckCircle2 className="w-5 h-5 text-green-400 shrink-0" />
                  <span>No password to remember</span>
                </div>
                <div className="flex items-center gap-3 text-white/60 text-sm">
                  <CheckCircle2 className="w-5 h-5 text-green-400 shrink-0" />
                  <span>Full control of your account</span>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Sign Message */}
          {isConnected && address && (
            <form onSubmit={handleLogin} className="space-y-5">
              {/* Wallet Connected Badge */}
              <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-green-500/20 rounded-full flex items-center justify-center">
                    <CheckCircle2 className="w-5 h-5 text-green-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-green-400">Wallet Connected</p>
                    <p className="text-xs text-green-300/60 font-mono truncate">
                      {address}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleDisconnect}
                    className="text-xs text-green-400 hover:text-green-300 transition-colors"
                  >
                    Change
                  </button>
                </div>
              </div>

              <div className="text-center space-y-3">
                <p className="text-white/80">
                  Click below to sign a message and verify your wallet ownership.
                </p>
                <p className="text-xs text-white/40">
                  This signature proves you own this wallet without sharing any private information.
                </p>
              </div>

              {/* Sign Message Button */}
              <Button
                type="submit"
                disabled={isLoading}
                className="w-full h-12 bg-linear-to-r from-[#F7931A] to-[#F97316] hover:from-[#FCD34D] hover:to-[#F7931A] text-white font-semibold text-base disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                    Signing in...
                  </span>
                ) : (
                  'Sign Message & Login'
                )}
              </Button>
            </form>
          )}

          {/* Divider */}
          <div className="relative mt-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/10"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-[#1e1b4b]/50 text-white/40">Or</span>
            </div>
          </div>

          {/* Sign Up Link */}
          <div className="mt-6 text-center">
            <p className="text-white/60 text-sm">
              Don&apos;t have an account?{' '}
              <Link
                href="/signup"
                className="text-[#FCD34D] hover:text-[#F7931A] font-semibold transition-colors"
              >
                Sign up
              </Link>
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-white/40 text-sm">
          <p>© 2025 Jarvis. Powered by Bitcoin L2.</p>
        </div>
      </div>
    </div>
  );
}
