# IP Agent - Story Protocol Integration

## Overview

The IP Agent handles registration of intellectual property assets on the [Story Protocol](https://story.foundation) blockchain. It integrates with the Visual Analyser to ensure images are unique before registration.

## Features

- ✅ Register images as IP Assets on Story Protocol
- ✅ Upload metadata and images to IPFS
- ✅ Attach license terms (commercial/non-commercial)
- ✅ Kafka integration for async processing
- ✅ REST API for direct registration

## Architecture

```
User (Frontend/App)
     ↓
Router Agent
     ↓
Visual Analyser (Check Uniqueness)
     ↓ (if unique)
Kafka: ip-registration-requests
     ↓
IP Agent
     ├→ Upload to IPFS
     ├→ Mint NFT
     └→ Register on Story Protocol
```

## Prerequisites

### 1. Story Protocol Wallet

You need an Ethereum wallet with:
- Private key for signing transactions
- Testnet tokens from [Story Faucet](https://faucet.story.foundation/)

### 2. Pinata Account

For IPFS storage:
- Sign up at [Pinata](https://pinata.cloud/)
- Create an API key (JWT)

### 3. Environment Setup

Copy `.env.template` to `.env` and fill in:

```bash
# Story Protocol Configuration  
WALLET_PRIVATE_KEY=0x... # Your wallet private key (keep secret!)
RPC_PROVIDER_URL=https://aeneid.storyrpc.io
CHAIN_ID=aeneid

# SPG NFT Contract
# Use public test contract or create your own
SPG_NFT_CONTRACT=0xc32A8a0FF3beDDDa58393d022aF433e78739FAbc

# Pinata for IPFS
PINATA_JWT=your_pinata_jwt_here

# Server Configuration
PORT=8085
KAFKA_BROKERS=kafka:29092
ENABLE_KAFKA=true

# Visual Analyser URL
VISUAL_ANALYSER_URL=http://localhost:8084
```

## Installation

```bash
cd agent/ip-agent

# Install dependencies
npm install

# Development
npm run dev

# Production
npm run build
npm start
```

## API Endpoints

### Health Check
```bash
GET /health
```

### Register IP Asset
```bash
POST /api/v1/ip/register
Content-Type: application/json

{
  "title": "My Artwork",
  "description": "A beautiful digital artwork",
  "imageData": "base64_encoded_image_here",
  "ownerAddress": "0x1234...5678", // Ethereum address that will own the IP
  "creatorName": "Artist Name",
  "tags": ["art", "digital"],
  "commercialUse": true,
  "commercialRevShare": 5, // 5% revenue share
  "mintingFee": "0.1" // 0.1 IP tokens to mint license
}
```

**Response:**
```json
{
  "success": true,
  "ipId": "0xabc...def",
  "txHash": "0x123...456",
  "tokenId": "1",
  "ipfsHash": "Qm...",
  "explorerUrl": "https://aeneid.explorer.story.foundation/ipa/0xabc...def"
}
```

### Attach License Terms
```bash
POST /api/v1/ip/attach-terms
Content-Type: application/json

{
  "ipId": "0xabc...def",
  "licenseTermsId": "1"
}
```

## Complete Flow with User Payment

### Option 1: Backend Wallet (Current Implementation)

The IP Agent uses a backend wallet to pay for transactions. **Not recommended for production** as it requires the backend to hold funds.

**Flow:**
1. User uploads image
2. Visual Analyser checks uniqueness  
3. If unique, IP Agent registers (backend pays)
4. User becomes owner of the IP

### Option 2: User Wallet (Recommended for Production)

The user pays for their own IP registration using their wallet (MetaMask, etc.)

**Flow:**
1. User uploads image via frontend app
2. Visual Analyser checks uniqueness
3. If unique, frontend prepares registration transaction
4. User reviews and signs transaction with their wallet
5. Transaction submitted to Story Protocol
6. IP registered with user as owner

**Implementation:**
- Use Story Protocol TypeScript SDK in the frontend
- See [React Setup Guide](https://docs.story.foundation/developers/react-guide/setup/overview)
- Frontend code example in `/app` directory

## Kafka Integration

The IP Agent listens to the `ip-registration-requests` Kafka topic for async processing.

**Message Format:**
```json
{
  "id": "msg_123",
  "user_id": "user_456",
  "asset_id": "asset_789",
  "owner_address": "0x1234...5678",
  "title": "My Artwork",
  "description": "Description here",
  "image_data": "base64_image",
  "commercial_use": true,
  "commercial_rev_share": 5,
  "minting_fee": "0.1",
  "timestamp": 1700000000
}
```

## Testing

### 1. Start Services

```bash
# Start all services
cd agent
docker-compose up -d
```

### 2. Test Registration

```bash
# Create test image (1x1 red pixel PNG)
IMAGE_B64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="

# Register IP
curl -X POST http://localhost:8085/api/v1/ip/register \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Test Artwork\",
    \"description\": \"A test image for IP registration\",
    \"imageData\": \"$IMAGE_B64\",
    \"ownerAddress\": \"0xYourEthereumAddress\",
    \"commercialUse\": true,
    \"commercialRevShare\": 5,
    \"mintingFee\": \"0.1\"
  }"
```

### 3. Check Story Explorer

Visit the `explorerUrl` from the response to see your registered IP on Story Protocol!

## License Types

### Non-Commercial
```json
{
  "commercialUse": false
}
```
- Free to use for non-commercial purposes
- Derivatives allowed
- Attribution required

### Commercial with Revenue Share
```json
{
  "commercialUse": true,
  "commercialRevShare": 5, // 5%
  "mintingFee": "0.1" // 0.1 IP tokens
}
```
- Commercial use allowed
- 5% revenue share to original creator
- 0.1 IP tokens to mint license

## Integration with Visual Analyser

The Visual Analyser checks image uniqueness before registration:

```go
// In visual_analyser/base/kafka_handler.go

// 1. Check uniqueness
results, err := vectorStore.SearchNearest(ctx, searchReq)

// 2. If unique, send to IP Agent
if results.Count == 0 || results.Results[0].Similarity < 0.85 {
    // Send IP registration request via Kafka
    kafka.SendIPRegistrationRequest(ctx, ipRegMsg)
}
```

## Cost Estimation

### Testnet (Aeneid)
- **Gas fees**: Free (testnet tokens from faucet)
- **IPFS storage**: Free tier available on Pinata

### Mainnet
- **Gas fees**: ~0.001-0.01 ETH per registration (varies)
- **IPFS storage**: Pinata pricing plans
- **Story Protocol fees**: Check latest on [docs](https://docs.story.foundation)

## Troubleshooting

### "Insufficient funds"
- Fund your wallet with testnet tokens: https://faucet.story.foundation/

### "PINATA_JWT not set"
- Set up Pinata account and add JWT to `.env`

### "Transaction reverted"
- Check wallet has enough tokens
- Verify SPG_NFT_CONTRACT is correct
- Check Story Protocol status

### "Image too large"
- Current limit: 50MB
- Recommend: Compress images before upload
- For larger images: Upload to IPFS first, then use IPFS hash

## Production Checklist

- [ ] Use secure key management (AWS KMS, HashiCorp Vault)
- [ ] Implement user wallet integration (MetaMask, WalletConnect)
- [ ] Add authentication & authorization
- [ ] Set up monitoring & logging
- [ ] Configure rate limiting
- [ ] Use mainnet RPC endpoint
- [ ] Test with real payments
- [ ] Set up error recovery
- [ ] Add database for tracking registrations
- [ ] Implement webhook callbacks for status updates

## References

- [Story Protocol Docs](https://docs.story.foundation/)
- [TypeScript SDK Setup](https://docs.story.foundation/developers/typescript-sdk/setup)
- [Register IP Asset](https://docs.story.foundation/developers/typescript-sdk/register-ip-asset)
- [Attach Terms](https://docs.story.foundation/developers/typescript-sdk/attach-terms)
- [React Integration](https://docs.story.foundation/developers/react-guide/setup/overview)
- [Story Explorer](https://aeneid.explorer.story.foundation/)

## Support

- Story Protocol Discord: https://discord.gg/storyprotocol
- Documentation: https://docs.story.foundation/
- GitHub: https://github.com/storyprotocol/

