'use client';

/**
 * IP Registration Component
 * 
 * This component provides a UI for users to:
 * 1. Upload an image
 * 2. Check uniqueness via Visual Analyser
 * 3. Register as IP on Story Protocol (user pays with wallet)
 */

import React, { useState } from 'react';
import { useWalletClient } from 'wagmi';
import { createStoryClient } from '@/lib/storyClient';
import { registerIPAsset, RegisterIPRequest } from '@/lib/ipRegistration';

export default function IPRegistration() {
  const { data: walletClient } = useWalletClient();
  
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string>('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [creatorName, setCreatorName] = useState('');
  const [commercialUse, setCommercialUse] = useState(false);
  const [revShare, setRevShare] = useState(5);
  const [mintingFee, setMintingFee] = useState('0.1');
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string>('');

  // Handle image selection
  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImageFile(file);
    
    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setImagePreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  // Handle registration
  const handleRegister = async () => {
    if (!imageFile || !title || !description || !walletClient) {
      setError('Please fill all required fields and connect wallet');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      // Convert image to base64
      const reader = new FileReader();
      reader.onloadend = async () => {
        const base64Image = (reader.result as string).split(',')[1];

        // Create Story Protocol client with user's wallet
        const storyClient = createStoryClient(walletClient);

        // Prepare request
        const request: RegisterIPRequest = {
          title,
          description,
          imageData: base64Image,
          creatorName: creatorName || walletClient.account.address,
          commercialUse,
          commercialRevShare: revShare,
          mintingFee,
        };

        // Register IP (this will prompt user to sign transaction)
        const response = await registerIPAsset(storyClient, request);

        if (response.success) {
          setResult(response);
        } else {
          setError(response.error || 'Registration failed');
        }

        setLoading(false);
      };

      reader.readAsDataURL(imageFile);
    } catch (err: any) {
      setError(err.message || 'An error occurred');
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h2 className="text-3xl font-bold mb-6 text-gray-800">
        Register Your IP on Story Protocol
      </h2>

      {/* Wallet Connection */}
      {!walletClient && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded">
          <p className="text-yellow-800">
            ⚠️ Please connect your wallet to continue
          </p>
        </div>
      )}

      {/* Image Upload */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Upload Image *
        </label>
        <input
          type="file"
          accept="image/*"
          onChange={handleImageChange}
          className="block w-full text-sm text-gray-500
            file:mr-4 file:py-2 file:px-4
            file:rounded-full file:border-0
            file:text-sm file:font-semibold
            file:bg-blue-50 file:text-blue-700
            hover:file:bg-blue-100"
        />
        {imagePreview && (
          <img
            src={imagePreview}
            alt="Preview"
            className="mt-4 max-w-xs rounded-lg shadow"
          />
        )}
      </div>

      {/* Title */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Title *
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g., My Digital Artwork"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Description */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Description *
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe your IP asset..."
          rows={4}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Creator Name */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Creator Name
        </label>
        <input
          type="text"
          value={creatorName}
          onChange={(e) => setCreatorName(e.target.value)}
          placeholder="Your name or artist name"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* License Options */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <h3 className="font-semibold text-gray-700 mb-3">License Terms</h3>
        
        <div className="mb-4">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={commercialUse}
              onChange={(e) => setCommercialUse(e.target.checked)}
              className="mr-2"
            />
            <span className="text-sm text-gray-700">
              Allow commercial use
            </span>
          </label>
        </div>

        {commercialUse && (
          <>
            <div className="mb-4">
              <label className="block text-sm text-gray-700 mb-1">
                Revenue Share: {revShare}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={revShare}
                onChange={(e) => setRevShare(Number(e.target.value))}
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">
                Licensees must share {revShare}% of revenue with you
              </p>
            </div>

            <div className="mb-4">
              <label className="block text-sm text-gray-700 mb-1">
                License Minting Fee (IP tokens)
              </label>
              <input
                type="text"
                value={mintingFee}
                onChange={(e) => setMintingFee(e.target.value)}
                placeholder="0.1"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
              <p className="text-xs text-gray-500 mt-1">
                Users pay this fee to mint a license
              </p>
            </div>
          </>
        )}
      </div>

      {/* Register Button */}
      <button
        onClick={handleRegister}
        disabled={loading || !walletClient || !imageFile || !title || !description}
        className="w-full bg-blue-600 text-white py-3 px-4 rounded-md font-semibold
          hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed
          transition-colors duration-200"
      >
        {loading ? '⏳ Registering...' : '🚀 Register IP Asset'}
      </button>

      {/* Status Messages */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded">
          <p className="text-red-800">❌ {error}</p>
        </div>
      )}

      {result && result.success && (
        <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded">
          <h3 className="font-semibold text-green-800 mb-2">
            ✅ IP Asset Registered Successfully!
          </h3>
          <div className="text-sm text-green-700 space-y-1">
            <p><strong>IP ID:</strong> {result.ipId}</p>
            <p><strong>Transaction:</strong> {result.txHash}</p>
            <p>
              <strong>View on Explorer:</strong>{' '}
              <a
                href={result.explorerUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                Open →
              </a>
            </p>
          </div>
        </div>
      )}

      {/* Info */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <h4 className="font-semibold text-blue-900 mb-2">📋 How it works:</h4>
        <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
          <li>Your image is checked for uniqueness</li>
          <li>Metadata is uploaded to IPFS</li>
          <li>An NFT is minted on Story Protocol</li>
          <li>Your IP is registered with license terms</li>
          <li><strong>You pay gas fees from your wallet</strong></li>
        </ol>
      </div>
    </div>
  );
}

