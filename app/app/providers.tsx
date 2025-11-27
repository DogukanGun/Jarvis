'use client';

import { WagmiProvider, createConfig, http } from 'wagmi';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConnectKitProvider, getDefaultConfig } from 'connectkit';

// Story Protocol Aeneid Testnet configuration
const storyChain = {
  id: 1305,
  name: 'Story Aeneid Testnet',
  nativeCurrency: {
    decimals: 18,
    name: 'IP',
    symbol: 'IP',
  },
  rpcUrls: {
    default: { http: ['https://aeneid.storyrpc.io'] },
    public: { http: ['https://aeneid.storyrpc.io'] },
  },
  blockExplorers: {
    default: {
      name: 'Story Explorer',
      url: 'https://aeneid.explorer.story.foundation',
    },
  },
  testnet: true,
} as const;

const config = createConfig(
  getDefaultConfig({
    appName: 'Jarvis IP Registration',
    walletConnectProjectId: process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || 'demo',
    chains: [storyChain as any],
    transports: {
      [storyChain.id]: http('https://aeneid.storyrpc.io'),
    },
  })
);

const queryClient = new QueryClient();

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <ConnectKitProvider>{children}</ConnectKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}

