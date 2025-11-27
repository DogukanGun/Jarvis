import { NextRequest, NextResponse } from 'next/server';
import { PinataSDK } from 'pinata';
import { createHash } from 'crypto';

// Initialize Pinata
let pinataInstance: PinataSDK | null = null;

function getPinata(): PinataSDK {
  if (!pinataInstance) {
    const pinataJwt = process.env.PINATA_JWT;
    if (!pinataJwt) {
      throw new Error('PINATA_JWT not configured in environment variables');
    }
    pinataInstance = new PinataSDK({
      pinataJwt: pinataJwt,
    });
  }
  return pinataInstance;
}

export async function POST(request: NextRequest) {
  try {
    const { type, data } = await request.json();

    if (!type || !data) {
      return NextResponse.json(
        { error: 'Missing required fields: type and data' },
        { status: 400 }
      );
    }

    const pinata = getPinata();
    let ipfsHash: string;

    if (type === 'image') {
      // Upload base64 image
      console.log('Uploading image to IPFS...');
      const imageBuffer = Buffer.from(data, 'base64');
      
      // Convert buffer to File
      const blob = new Blob([imageBuffer], { type: 'image/png' });
      const file = new File([blob], 'image.png', { type: 'image/png' });
      
      const result = await pinata.upload.file(file);
      ipfsHash = result.IpfsHash;
      
      console.log(`Image uploaded to IPFS: ${ipfsHash}`);
    } else {
      // Upload JSON metadata
      console.log('Uploading metadata to IPFS...');
      const result = await pinata.upload.json(data);
      ipfsHash = result.IpfsHash;
      
      console.log(`Metadata uploaded to IPFS: ${ipfsHash}`);
    }

    // Calculate content hash
    const contentHash = createHash('sha256')
      .update(typeof data === 'string' ? data : JSON.stringify(data))
      .digest('hex');

    return NextResponse.json({
      ipfsHash,
      contentHash,
      url: `https://ipfs.io/ipfs/${ipfsHash}`,
    });
  } catch (error: any) {
    console.error('IPFS upload error:', error);
    
    // Check if it's a Pinata configuration error
    if (error.message.includes('PINATA_JWT')) {
      return NextResponse.json(
        { 
          error: 'IPFS service not configured. Please contact administrator.',
          details: 'PINATA_JWT environment variable is missing'
        },
        { status: 503 }
      );
    }
    
    return NextResponse.json(
      { 
        error: 'Failed to upload to IPFS',
        details: error.message 
      },
      { status: 500 }
    );
  }
}

