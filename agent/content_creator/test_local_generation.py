#!/usr/bin/env python3
"""
Local generation test - bypasses Kafka to test model directly.

Usage:
    python test_local_generation.py
"""
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_image_generation():
    """Test image generation directly without Kafka."""
    print("=" * 60)
    print("LOCAL IMAGE GENERATION TEST")
    print("=" * 60)

    # Check device
    from app.clients.model_client import get_best_device, get_torch_dtype
    device = get_best_device()
    dtype = get_torch_dtype(device)
    print(f"Device: {device}")
    print(f"Dtype: {dtype}")

    # Load model
    print("\nLoading model...")
    from app.clients.model_client import get_image_model
    pipeline = get_image_model()
    print(f"Model loaded: {type(pipeline).__name__}")

    # Generate image
    prompt = "A beautiful sunset over snow-capped mountains, golden hour lighting, photorealistic"
    print(f"\nPrompt: {prompt}")
    print("Generating image (512x512, 20 steps)...")

    import torch
    gen_device = "cpu" if device == "mps" else device
    generator = torch.Generator(device=gen_device).manual_seed(42)

    result = pipeline(
        prompt=prompt,
        width=512,
        height=512,
        num_inference_steps=20,
        guidance_scale=7.5,
        generator=generator,
    )

    image = result.images[0]

    # Save result
    output_dir = Path("simulation_output")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "test_local_generation.png"
    image.save(output_path)

    print(f"\nImage saved to: {output_path}")
    print("=" * 60)
    print("TEST PASSED!")
    print("=" * 60)

    return str(output_path)


if __name__ == "__main__":
    try:
        output_path = test_image_generation()
        print(f"\nOpen the generated image: open {output_path}")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
