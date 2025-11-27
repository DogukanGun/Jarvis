import { Router, Request, Response } from 'express';
import { ipRegistrationService, RegisterIPRequest } from '../services/ipRegistration';
import { Address } from 'viem';

const router = Router();

// Health check
router.get('/health', (req: Request, res: Response) => {
  res.json({
    status: 'healthy',
    service: 'ip-agent',
    timestamp: new Date().toISOString(),
  });
});

// Register IP Asset
router.post('/api/v1/ip/register', async (req: Request, res: Response) => {
  try {
    const {
      title,
      description,
      imageData,
      ownerAddress,
      creatorName,
      tags,
      commercialUse,
      commercialRevShare,
      mintingFee,
      derivativesAllowed,
    } = req.body;

    // Validation
    if (!title || !description || !imageData || !ownerAddress) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields: title, description, imageData, ownerAddress',
      });
    }

    // Validate Ethereum address
    if (!/^0x[a-fA-F0-9]{40}$/.test(ownerAddress)) {
      return res.status(400).json({
        success: false,
        error: 'Invalid Ethereum address format',
      });
    }

    const request: RegisterIPRequest = {
      title,
      description,
      imageData,
      ownerAddress: ownerAddress as Address,
      creatorName,
      tags,
      commercialUse: commercialUse !== undefined ? commercialUse : false,
      commercialRevShare: commercialRevShare || 5,
      mintingFee: mintingFee || '0.1',
      derivativesAllowed: derivativesAllowed !== undefined ? derivativesAllowed : true,
    };

    console.log(`Registering IP: "${title}" for owner ${ownerAddress}`);

    const result = await ipRegistrationService.registerIP(request);

    if (result.success) {
      return res.status(201).json(result);
    } else {
      return res.status(500).json(result);
    }
  } catch (error: any) {
    console.error('Error in /api/v1/ip/register:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Internal server error',
    });
  }
});

// Attach license terms to existing IP
router.post('/api/v1/ip/attach-terms', async (req: Request, res: Response) => {
  try {
    const { ipId, licenseTermsId } = req.body;

    if (!ipId || !licenseTermsId) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields: ipId, licenseTermsId',
      });
    }

    const result = await ipRegistrationService.attachLicenseTerms(
      ipId as Address,
      BigInt(licenseTermsId)
    );

    return res.json(result);
  } catch (error: any) {
    console.error('Error in /api/v1/ip/attach-terms:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Internal server error',
    });
  }
});

export default router;

