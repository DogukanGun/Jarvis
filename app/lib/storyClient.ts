/**
 * Story Protocol Client Configuration
 * 
 * This module sets up the Story Protocol SDK for frontend use with user wallets.
 * Users sign and pay for their own IP registration transactions.
 */

import { StoryClient, StoryConfig } from '@story-protocol/core-sdk';
import { http } from 'viem';

/**
 * Initialize Story Protocol client with user's wallet
 * 
 * @param walletClient - Viem wallet client from wagmi or similar
 * @returns Configured Story Protocol client
 */
export function createStoryClient(walletClient: any): StoryClient {
  const config: StoryConfig = {
    account: walletClient.account,
    transport: http(process.env.NEXT_PUBLIC_RPC_PROVIDER_URL || 'https://aeneid.storyrpc.io'),
    chainId: (process.env.NEXT_PUBLIC_CHAIN_ID as any) || 'aeneid',
  };

  return StoryClient.newClient(config);
}

/**
 * Chain configuration for Story Protocol
 */
export const storyChain = {
  id: 'aeneid',
  name: 'Story Aeneid Testnet',
  rpcUrls: {
    default: { http: ['https://aeneid.storyrpc.io'] },
    public: { http: ['https://aeneid.storyrpc.io'] },
  },
  blockExplorers: {
    default: { 
      name: 'Story Explorer', 
      url: 'https://aeneid.explorer.story.foundation' 
    },
  },
  testnet: true,
};

