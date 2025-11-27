/**
 * IP Registration Service
 * 
 * Handles the complete flow of registering an IP asset:
 * 1. Check uniqueness via Visual Analyser
 * 2. Upload to IPFS
 * 3. Register on Story Protocol (user pays)
 */

import { StoryClient, IpMetadata } from '@story-protocol/core-sdk';
import { parseEther, Address } from 'viem';

export interface CheckUniquenessRequest {
  imageData: string; // base64
}

export interface CheckUniquenessResponse {
  isUnique: boolean;
  similarity?: number;
  conflictingAssetId?: string;
}

export interface RegisterIPRequest {
  title: string;
  description: string;
  imageData: string; // base64
  creatorName?: string;
  tags?: string[];
  // License configuration
  commercialUse?: boolean;
  commercialRevShare?: number; // 0-100
  mintingFee?: string; // in ETH
}

export interface RegisterIPResponse {
  success: boolean;
  ipId?: string;
  txHash?: string;
  tokenId?: string;
  explorerUrl?: string;
  error?: string;
}

/**
 * Check if image is unique using Visual Analyser
 */
export async function checkImageUniqueness(
  imageData: string
): Promise<CheckUniquenessResponse> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_VISUAL_ANALYSER_URL || 'http://localhost:8084'}/api/check`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_data: imageData,
        threshold: 0.85,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(`Visual Analyser error: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Upload JSON metadata to IPFS via backend service
 * (Alternative: upload directly from frontend using Pinata SDK)
 */
async function uploadToIPFS(data: any): Promise<{ ipfsHash: string; contentHash: string }> {
  const response = await fetch('/api/ipfs/upload', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error('Failed to upload to IPFS');
  }

  return response.json();
}

/**
 * Register IP Asset on Story Protocol
 * This function triggers a wallet transaction that the user must sign and pay for.
 */
export async function registerIPAsset(
  storyClient: StoryClient,
  request: RegisterIPRequest
): Promise<RegisterIPResponse> {
  try {
    // 1. Check uniqueness first
    console.log('Checking image uniqueness...');
    const uniquenessCheck = await checkImageUniqueness(request.imageData);

    if (!uniquenessCheck.isUnique) {
      return {
        success: false,
        error: `Image is too similar to existing asset (${uniquenessCheck.similarity}% match)`,
      };
    }

    console.log('✓ Image is unique');

    // 2. Upload image to IPFS
    console.log('Uploading image to IPFS...');
    const imageBuffer = Buffer.from(request.imageData, 'base64');
    const imageIpfs = await uploadToIPFS({
      type: 'image',
      data: request.imageData,
    });
    const imageUrl = `https://ipfs.io/ipfs/${imageIpfs.ipfsHash}`;
    console.log(`✓ Image uploaded: ${imageUrl}`);

    // 3. Prepare IP Metadata
    const ipMetadata: IpMetadata = {
      title: request.title,
      description: request.description,
      image: imageUrl,
      imageHash: `0x${imageIpfs.contentHash}`,
      mediaUrl: imageUrl,
      mediaHash: `0x${imageIpfs.contentHash}`,
      mediaType: 'image/png',
      creators: [
        {
          name: request.creatorName || 'Anonymous',
          address: storyClient.account.address as Address,
          contributionPercent: 100,
        },
      ],
    };

    if (request.tags && request.tags.length > 0) {
      (ipMetadata as any).tags = request.tags;
    }

    // 4. Upload IP metadata to IPFS
    console.log('Uploading metadata to IPFS...');
    const ipMetadataIpfs = await uploadToIPFS({
      type: 'metadata',
      data: ipMetadata,
    });
    console.log(`✓ Metadata uploaded`);

    // 5. Prepare NFT metadata
    const nftMetadata = {
      name: `${request.title} - Ownership NFT`,
      description: `This NFT represents ownership of the IP: ${request.description}`,
      image: imageUrl,
    };

    const nftMetadataIpfs = await uploadToIPFS({
      type: 'nft-metadata',
      data: nftMetadata,
    });

    // 6. Prepare license terms
    // Note: License terms will be handled by Story Protocol SDK
    // For v1.4.2, we'll use basic registration without custom license terms
    // Check SDK docs for latest license term API: https://docs.story.foundation/

    // 7. Register IP Asset (triggers wallet transaction)
    console.log('Registering IP Asset on Story Protocol...');
    console.log('⏳ Please sign the transaction in your wallet...');

    const spgNftContract = (process.env.NEXT_PUBLIC_SPG_NFT_CONTRACT || 
      '0xc32A8a0FF3beDDDa58393d022aF433e78739FAbc') as Address;

    const response = await storyClient.ipAsset.register({
      nftContract: spgNftContract,
      tokenId: '0', // Will be generated
      metadata: {
        metadataURI: `https://ipfs.io/ipfs/${ipMetadataIpfs.ipfsHash}`,
        metadataHash: `0x${ipMetadataIpfs.contentHash}`,
        nftMetadataURI: `https://ipfs.io/ipfs/${nftMetadataIpfs.ipfsHash}`,
        nftMetadataHash: `0x${nftMetadataIpfs.contentHash}`,
      },
    } as any); // Type assertion for SDK compatibility

    console.log('✓ IP Asset registered successfully!');
    console.log(`IP ID: ${response.ipId}`);
    console.log(`Transaction: ${response.txHash}`);

    const explorerUrl = `https://aeneid.explorer.story.foundation/ipa/${response.ipId}`;

    return {
      success: true,
      ipId: response.ipId,
      txHash: response.txHash,
      tokenId: response.tokenId?.toString(),
      explorerUrl: explorerUrl,
    };
  } catch (error: any) {
    console.error('Error registering IP:', error);
    return {
      success: false,
      error: error.message || 'Registration failed',
    };
  }
}

