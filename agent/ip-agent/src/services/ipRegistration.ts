import { getStoryClient } from '../config/storyClient';
import { uploadJSONToIPFS, uploadImageToIPFS } from '../utils/ipfs';
import { IpMetadata, PILFlavor, WIP_TOKEN_ADDRESS } from '@story-protocol/core-sdk';
import { parseEther, Address } from 'viem';

export interface RegisterIPRequest {
  title: string;
  description: string;
  imageData: string; // base64 encoded image
  ownerAddress: Address;
  creatorName?: string;
  tags?: string[];
  // Licensing configuration
  commercialUse?: boolean;
  commercialRevShare?: number; // percentage (0-100)
  mintingFee?: string; // in ETH
  derivativesAllowed?: boolean;
}

export interface RegisterIPResponse {
  success: boolean;
  ipId?: string;
  txHash?: string;
  tokenId?: string;
  ipfsHash?: string;
  explorerUrl?: string;
  error?: string;
}

export class IPRegistrationService {
  async registerIP(request: RegisterIPRequest): Promise<RegisterIPResponse> {
    try {
      const client = getStoryClient();

      // 1. Decode base64 image
      const imageBuffer = Buffer.from(request.imageData, 'base64');
      console.log(`Image decoded: ${imageBuffer.length} bytes`);

      // 2. Upload image to IPFS
      console.log('Uploading image to IPFS...');
      const imageIpfs = await uploadImageToIPFS(imageBuffer);
      const imageUrl = `https://ipfs.io/ipfs/${imageIpfs.ipfsHash}`;
      console.log(`Image uploaded to IPFS: ${imageUrl}`);

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
            address: request.ownerAddress,
            contributionPercent: 100,
          },
        ],
      };

      // Add tags if provided
      if (request.tags && request.tags.length > 0) {
        (ipMetadata as any).tags = request.tags;
      }

      // 4. Upload IP Metadata to IPFS
      console.log('Uploading IP metadata to IPFS...');
      const ipMetadataIpfs = await uploadJSONToIPFS(ipMetadata);
      console.log(`IP metadata uploaded to IPFS: ${ipMetadataIpfs.ipfsHash}`);

      // 5. Prepare NFT Metadata
      const nftMetadata = {
        name: `${request.title} - Ownership NFT`,
        description: `This NFT represents ownership of the IP: ${request.description}`,
        image: imageUrl,
      };

      // 6. Upload NFT Metadata to IPFS
      console.log('Uploading NFT metadata to IPFS...');
      const nftMetadataIpfs = await uploadJSONToIPFS(nftMetadata);
      console.log(`NFT metadata uploaded to IPFS: ${nftMetadataIpfs.ipfsHash}`);

      // 7. Prepare license terms (if commercial use is enabled)
      const licenseTermsData = [];
      if (request.commercialUse) {
        const revShare = request.commercialRevShare || 5; // default 5%
        const mintFee = request.mintingFee || '0.1'; // default 0.1 IP tokens
        
        licenseTermsData.push({
          terms: PILFlavor.commercialRemix({
            commercialRevShare: revShare,
            defaultMintingFee: parseEther(mintFee),
            currency: WIP_TOKEN_ADDRESS,
          }),
        });

        console.log(`License terms prepared: ${revShare}% rev share, ${mintFee} IP minting fee`);
      } else {
        // Non-commercial license
        licenseTermsData.push({
          terms: PILFlavor.nonCommercialSocialRemixing(),
        });
        console.log('License terms: Non-commercial social remixing');
      }

      // 8. Register IP Asset
      console.log('Registering IP Asset on Story Protocol...');
      const spgNftContract = process.env.SPG_NFT_CONTRACT as Address;
      
      if (!spgNftContract) {
        throw new Error('SPG_NFT_CONTRACT not configured');
      }

      const response = await client.ipAsset.registerIpAsset({
        nft: {
          type: 'mint',
          spgNftContract: spgNftContract,
        },
        ipMetadata: {
          ipMetadataURI: `https://ipfs.io/ipfs/${ipMetadataIpfs.ipfsHash}`,
          ipMetadataHash: `0x${ipMetadataIpfs.contentHash}`,
          nftMetadataURI: `https://ipfs.io/ipfs/${nftMetadataIpfs.ipfsHash}`,
          nftMetadataHash: `0x${nftMetadataIpfs.contentHash}`,
        },
        licenseTermsData: licenseTermsData,
      });

      console.log(`IP Asset registered successfully!`);
      console.log(`IP ID: ${response.ipId}`);
      console.log(`Transaction Hash: ${response.txHash}`);
      console.log(`Token ID: ${response.tokenId}`);

      const explorerUrl = `https://aeneid.explorer.story.foundation/ipa/${response.ipId}`;

      return {
        success: true,
        ipId: response.ipId,
        txHash: response.txHash,
        tokenId: response.tokenId?.toString(),
        ipfsHash: ipMetadataIpfs.ipfsHash,
        explorerUrl: explorerUrl,
      };
    } catch (error: any) {
      console.error('Error registering IP:', error);
      return {
        success: false,
        error: error.message || 'Unknown error occurred',
      };
    }
  }

  async attachLicenseTerms(ipId: Address, licenseTermsId: bigint): Promise<{
    success: boolean;
    txHash?: string;
    error?: string;
  }> {
    try {
      const client = getStoryClient();

      const response = await client.license.attachLicenseTerms({
        licenseTermsId: licenseTermsId,
        ipId: ipId,
      });

      return {
        success: response.success,
        txHash: response.txHash,
      };
    } catch (error: any) {
      console.error('Error attaching license terms:', error);
      return {
        success: false,
        error: error.message,
      };
    }
  }
}

export const ipRegistrationService = new IPRegistrationService();

