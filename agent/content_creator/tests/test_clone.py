#!/usr/bin/env python3
"""
Test script to demonstrate model cloning and running functionality.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import the client
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.clients.model_client.client import ModelClient


def test_model_cloning():
    """Test the model cloning functionality."""
    
    print("Initializing ModelClient...")
    client = ModelClient()
    
    # Example model to clone (using a lightweight model for testing)
    model_id = "sshleifer/tiny-gpt2"  # Small test model
    
    print(f"\nCloning model: {model_id}")
    try:
        model_path = client.clone_model(model_id)
        print(f"Model cloned successfully to: {model_path}")
        
        # Load the cloned model
        print("\nLoading the cloned model...")
        local_model = client.load_local_model(model_path, model_type="text-generation")
        
        print("Model loaded successfully!")
        print(f"Model type: {type(local_model)}")
        
        # If it's a text generation model, show basic info
        if isinstance(local_model, dict) and "model" in local_model:
            print(f"Model: {local_model['model'].__class__.__name__}")
            print(f"Tokenizer: {local_model['tokenizer'].__class__.__name__}")
        
        print("\nModel cloning and loading test completed successfully!")
        
    except Exception as e:
        print(f"Error during model cloning/loading: {e}")
        import traceback
        traceback.print_exc()


def test_image_model():
    """Test with a small image model."""
    
    print("\n" + "="*50)
    print("Testing with a small image model...")
    
    client = ModelClient()
    
    # Using a small Stable Diffusion model for testing
    model_id = "hf-internal-testing/tiny-stable-diffusion-torch"
    
    print(f"\nCloning image model: {model_id}")
    try:
        model_path = client.clone_model(model_id)
        print(f"Image model cloned successfully to: {model_path}")
        
        # Load the cloned image model
        print("\nLoading the cloned image model...")
        local_pipeline = client.load_local_model(model_path, model_type="image")
        
        print("Image model loaded successfully!")
        print(f"Pipeline type: {type(local_pipeline).__name__}")
        
        print("\nImage model cloning and loading test completed successfully!")
        
    except Exception as e:
        print(f"Error during image model cloning/loading: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Testing Hugging Face Model Cloning and Local Execution")
    print("="*60)
    
    test_model_cloning()
    test_image_model()
    
    print("\n" + "="*60)
    print("All tests completed!")