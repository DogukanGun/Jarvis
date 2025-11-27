import { PinataSDK } from 'pinata';
import { createHash } from 'crypto';

let pinataInstance: PinataSDK | null = null;

function getPinata(): PinataSDK {
  if (!pinataInstance) {
    const pinataJwt = process.env.PINATA_JWT;
    if (!pinataJwt) {
      throw new Error('PINATA_JWT not set in environment');
    }
    pinataInstance = new PinataSDK({
      pinataJwt: pinataJwt,
    });
  }
  return pinataInstance;
}

export async function uploadJSONToIPFS(jsonMetadata: any): Promise<{
  ipfsHash: string;
  contentHash: string;
}> {
  const pinata = getPinata();
  const { IpfsHash } = await pinata.upload.json(jsonMetadata);
  
  const contentHash = createHash('sha256')
    .update(JSON.stringify(jsonMetadata))
    .digest('hex');

  return {
    ipfsHash: IpfsHash,
    contentHash: contentHash,
  };
}

export async function uploadImageToIPFS(imageBuffer: Buffer): Promise<{
  ipfsHash: string;
  contentHash: string;
}> {
  const pinata = getPinata();
  
  // Convert buffer to File object
  const blob = new Blob([imageBuffer]);
  const file = new File([blob], 'image.png', { type: 'image/png' });
  
  const { IpfsHash } = await pinata.upload.file(file);
  
  const contentHash = createHash('sha256')
    .update(imageBuffer)
    .digest('hex');

  return {
    ipfsHash: IpfsHash,
    contentHash: contentHash,
  };
}

