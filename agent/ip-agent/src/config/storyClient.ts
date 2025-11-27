import { StoryClient, StoryConfig } from '@story-protocol/core-sdk';
import { http } from 'viem';
import { privateKeyToAccount, Address, Account } from 'viem/accounts';

let clientInstance: StoryClient | null = null;

export function initializeStoryClient(): StoryClient {
  if (clientInstance) {
    return clientInstance;
  }

  const privateKey = process.env.WALLET_PRIVATE_KEY;
  if (!privateKey) {
    throw new Error('WALLET_PRIVATE_KEY not set in environment');
  }

  const privateKeyAddress: Address = `0x${privateKey.replace('0x', '')}`;
  const account: Account = privateKeyToAccount(privateKeyAddress);

  const config: StoryConfig = {
    account: account,
    transport: http(process.env.RPC_PROVIDER_URL || 'https://aeneid.storyrpc.io'),
    chainId: (process.env.CHAIN_ID as any) || 'aeneid',
  };

  clientInstance = StoryClient.newClient(config);
  console.log('Story Protocol client initialized');
  console.log('Account address:', account.address);

  return clientInstance;
}

export function getStoryClient(): StoryClient {
  if (!clientInstance) {
    return initializeStoryClient();
  }
  return clientInstance;
}

