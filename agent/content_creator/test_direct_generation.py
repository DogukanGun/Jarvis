#!/usr/bin/env python3
"""
Direct generation test - tests the graph without Kafka.

This directly invokes the image generation graph to verify
the model works correctly with proper parameters.

Usage:
    python test_direct_generation.py
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_direct_image_generation():
    """Test image generation graph directly (no Kafka)."""
    print("=" * 60)
    print("DIRECT IMAGE GENERATION TEST")
    print("=" * 60)

    from app.clients.model_client import get_best_device
    device = get_best_device()
    print(f"Device: {device}")

    # Create a test request with small image size (512x512 works on MPS)
    job_id = f"direct-{uuid.uuid4().hex[:8]}"
    request = {
        "job_id": job_id,
        "task": "image_from_prompt",
        "prompt": "A majestic lion standing on a rock at sunset, photorealistic, 8k quality",
        "output": {
            "format": "png",
            "width": 512,
            "height": 512,
        },
        "meta": {
            "guidance_scale": 7.5,
            "num_inference_steps": 20,  # Reduced for faster testing
            "seed": 42,
        },
    }

    print(f"\nJob ID: {job_id}")
    print(f"Prompt: {request['prompt'][:50]}...")
    print(f"Size: {request['output']['width']}x{request['output']['height']}")
    print(f"Steps: {request['meta']['num_inference_steps']}")

    # Run the image prompt graph directly
    print("\nRunning image generation graph...")
    from app.graphs.image_prompt_graph import run_image_prompt_graph
    result = run_image_prompt_graph(request)

    print("\n" + "=" * 60)

    if result.get("success"):
        print("RESULT: SUCCESS")
        url = result.get("response_url", "No URL")
        print(f"URL: {url}")

        # Try to download the image
        if url and url.startswith("http"):
            try:
                import requests
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    output_dir = Path("simulation_output")
                    output_dir.mkdir(exist_ok=True)
                    output_path = output_dir / f"{job_id}.png"
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    print(f"Downloaded to: {output_path}")
            except Exception as e:
                print(f"Download failed: {e}")
    else:
        print("RESULT: FAILED")
        print(f"Error: {result.get('error', 'Unknown error')}")

    print("=" * 60)
    return result


if __name__ == "__main__":
    result = test_direct_image_generation()
    if result.get("success"):
        print("\nTest PASSED!")
    else:
        print("\nTest FAILED!")
        sys.exit(1)
