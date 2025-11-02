'use client';

import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sparkles, User, Mail, CheckCircle2, CreditCard, AlertCircle, Lock, Eye, EyeOff } from 'lucide-react';
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAccount, useSignMessage, useDisconnect } from 'wagmi';
import { ConnectButton } from '@rainbow-me/rainbowkit';
import { apiClient } from "@/lib/api-client";
import { toast } from "sonner";

const SUBSCRIPTION_PRICE_BTC = "0.0003"; // BTC (approximately $29.99)
const BITCOIN_ADDRESS = "0x23aB3f13502B1D2A90373d618D1387197006B8C1"; // Replace with actual Bitcoin address

export default function SignupPage() {
  const router = useRouter();
  const { address, isConnected } = useAccount();
  const { signMessageAsync } = useSignMessage();
  const { disconnect } = useDisconnect();
  
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [paymentStep, setPaymentStep] = useState<'details' | 'confirming'>('details');
  const [btcTxId, setBtcTxId] = useState('');

  const handleChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleCopyAddress = () => {
    navigator.clipboard.writeText(BITCOIN_ADDRESS);
    toast.success('Bitcoin address copied to clipboard!');
  };

  const handleConfirmPayment = () => {
    if (!btcTxId.trim()) {
      toast.error('Please enter your Bitcoin transaction ID');
      return;
    }
    
    setPaymentStep('confirming');
    toast.success('Payment submitted!', {
      description: 'You can now complete your signup',
    });
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!address) {
      toast.error('Please connect your wallet first');
      return;
    }

    if (!formData.fullName.trim() || !formData.email.trim() || !formData.password.trim()) {
      toast.error('Please fill in all required fields');
      return;
    }

    if (!btcTxId.trim()) {
      toast.error('Please enter your Bitcoin transaction ID');
      return;
    }
    
    setIsLoading(true);
    
    try {
      // Create message to sign
      const message = `Sign this message to authenticate with Jarvis AI.\n\nWallet: ${address}\nTimestamp: ${Date.now()}`;
      
      // Request signature from wallet
      const signature = await signMessageAsync({ message });
      
      // Call backend API with wallet auth including BTC transaction ID
      const response = await apiClient.auth.walletAuth({
        wallet_address: address,
        signature,
        message,
        full_name: formData.fullName,
        email: formData.email,
        password: formData.password,
        btc_tx_id: btcTxId, // Include Bitcoin transaction ID
      });
      
      // Save token and user data
      if (typeof window !== 'undefined') {
        localStorage.setItem('auth-token', response.token);
        localStorage.setItem('user', JSON.stringify(response));
      }
      
      // Show success toast
      toast.success('Account created successfully!', {
        description: 'Redirecting to dashboard...',
      });
      
      // Redirect to dashboard after 1.5 seconds
      setTimeout(() => {
        router.push('/dashboard');
      }, 1500);
    } catch (err) {
      console.error('Signup error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Wallet authentication failed. Please try again.';
      toast.error('Authentication failed', {
        description: errorMessage,
      });
      setIsLoading(false);
    }
  };

  const handleDisconnect = () => {
    disconnect();
    setFormData({ fullName: '', email: '', password: '' });
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
          <h1 className="text-3xl font-bold text-white mb-2">Create your account</h1>
          <p className="text-white/60">Connect your wallet to get started</p>
        </div>

        {/* Signup Card */}
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
                  No passwords needed. Sign in securely using your Web3 wallet.
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

          {/* Step 2: Optional Profile Details + Sign */}
          {isConnected && address && (
            <form onSubmit={handleSignup} className="space-y-5">
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

              {/* Payment Section */}
              <div className="bg-[#F7931A]/10 border border-[#F7931A]/20 rounded-lg p-5 space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-[#F7931A]/20 rounded-full flex items-center justify-center shrink-0">
                    <CreditCard className="w-5 h-5 text-[#F7931A]" />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-base font-semibold text-white mb-1">Monthly Subscription</h4>
                    <p className="text-sm text-white/60 mb-3">
                      Pay {SUBSCRIPTION_PRICE_BTC} BTC ($29.99) per month to access Jarvis AI services
                    </p>
                    
                    {paymentStep === 'details' && (
                      <div className="space-y-3">
                        <div className="bg-white/5 rounded-lg p-3 space-y-2">
                          <div className="flex justify-between text-sm">
                            <span className="text-white/60">Subscription Fee</span>
                            <span className="text-white font-medium">{SUBSCRIPTION_PRICE_BTC} BTC</span>
                          </div>
                          <div className="space-y-1">
                            <span className="text-white/40 text-xs">Bitcoin Address:</span>
                            <div className="flex items-center gap-2">
                              <code className="flex-1 text-white/80 font-mono text-xs bg-black/20 px-2 py-1.5 rounded break-all">
                                {BITCOIN_ADDRESS}
                              </code>
                              <button
                                type="button"
                                onClick={handleCopyAddress}
                                className="text-[#F7931A] hover:text-[#FCD34D] text-xs font-medium whitespace-nowrap"
                              >
                                Copy
                              </button>
                            </div>
                          </div>
                        </div>
                        
                        <div className="space-y-2">
                          <Label htmlFor="btcTxId" className="text-white/80 text-xs">
                            Bitcoin Transaction ID
                          </Label>
                          <Input
                            id="btcTxId"
                            type="text"
                            placeholder="Enter your BTC transaction ID after payment"
                            value={btcTxId}
                            onChange={(e) => setBtcTxId(e.target.value)}
                            className="bg-white/5 border-white/10 text-white placeholder:text-white/40 focus:border-[#F7931A]/50 text-sm"
                          />
                        </div>
                        
                        <Button
                          type="button"
                          onClick={handleConfirmPayment}
                          disabled={!btcTxId.trim()}
                          className="w-full bg-[#F7931A] hover:bg-[#FCD34D] text-white font-semibold"
                        >
                          Confirm Payment
                        </Button>
                      </div>
                    )}

                    {paymentStep === 'confirming' && (
                      <div className="flex items-center gap-2 text-sm text-green-400">
                        <CheckCircle2 className="w-5 h-5" />
                        <span>Payment submitted! Complete signup below.</span>
                      </div>
                    )}
                  </div>
                </div>

                {paymentStep !== 'confirming' && (
                  <div className="flex items-start gap-2 bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3">
                    <AlertCircle className="w-4 h-4 text-yellow-400 mt-0.5 shrink-0" />
                    <p className="text-xs text-yellow-200/80">
                      Send {SUBSCRIPTION_PRICE_BTC} BTC to the address above, then enter the transaction ID to continue
                    </p>
                  </div>
                )}
              </div>

              <div className="space-y-4">
                <p className="text-sm text-white/60">
                  Complete your profile to continue
                </p>

                {/* Full Name Field */}
                <div className="space-y-2">
                  <Label htmlFor="fullName" className="text-white/80">
                    Full Name <span className="text-red-400">*</span>
                  </Label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                    <Input
                      id="fullName"
                      type="text"
                      placeholder="John Doe"
                      value={formData.fullName}
                      onChange={(e) => handleChange('fullName', e.target.value)}
                      className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-white/40 focus:border-[#F7931A]/50 h-12"
                      disabled={paymentStep !== 'confirming'}
                      required
                    />
                  </div>
                </div>

                {/* Email Field */}
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-white/80">
                    Email <span className="text-red-400">*</span>
                  </Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                    <Input
                      id="email"
                      type="email"
                      placeholder="you@example.com"
                      value={formData.email}
                      onChange={(e) => handleChange('email', e.target.value)}
                      className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-white/40 focus:border-[#F7931A]/50 h-12"
                      disabled={paymentStep !== 'confirming'}
                      required
                    />
                  </div>
                </div>

                {/* Password Field */}
                <div className="space-y-2">
                  <Label htmlFor="password" className="text-white/80">
                    Password <span className="text-red-400">*</span>
                  </Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={formData.password}
                      onChange={(e) => handleChange('password', e.target.value)}
                      className="pl-10 pr-10 bg-white/5 border-white/10 text-white placeholder:text-white/40 focus:border-[#F7931A]/50 h-12"
                      disabled={paymentStep !== 'confirming'}
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/60"
                    >
                      {showPassword ? (
                        <EyeOff className="w-5 h-5" />
                      ) : (
                        <Eye className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </div>
              </div>

              {/* Sign Message Button */}
              <Button
                type="submit"
                disabled={isLoading || paymentStep !== 'confirming' || !formData.fullName.trim() || !formData.email.trim() || !formData.password.trim()}
                className="w-full h-12 bg-linear-to-r from-[#F7931A] to-[#F97316] hover:from-[#FCD34D] hover:to-[#F7931A] text-white font-semibold text-base disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                    Creating account...
                  </span>
                ) : paymentStep !== 'confirming' ? (
                  'Complete Payment First'
                ) : !formData.fullName.trim() || !formData.email.trim() || !formData.password.trim() ? (
                  'Fill Required Fields'
                ) : (
                  'Sign & Create Account'
                )}
              </Button>

              {paymentStep === 'confirming' && (
                <p className="text-xs text-white/40 text-center">
                  You&apos;ll be asked to sign a message to verify your wallet ownership
                </p>
              )}
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

          {/* Login Link */}
          <div className="mt-6 text-center">
            <p className="text-white/60 text-sm">
              Already have an account?{' '}
              <Link
                href="/login"
                className="text-[#FCD34D] hover:text-[#F7931A] font-semibold transition-colors"
              >
                Sign in
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
