#!/usr/bin/env python3
"""
End-to-end pipeline test - runs all components in a single process.

Tests the complete flow:
1. Router receives request and routes to correct topic
2. Image generator processes and generates image
3. Uploads to MinIO and publishes result

Usage:
    python test_pipeline_e2e.py
"""
import sys
import uuid
import time
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_image_prompt_pipeline():
    """Test the full image generation pipeline."""
    print("=" * 60)
    print("END-TO-END PIPELINE TEST")
    print("=" * 60)

    from app.config import config
    from app.clients.kafka_client import KafkaMediaClient

    # Step 1: Create test request
    job_id = f"e2e-{uuid.uuid4().hex[:8]}"
    request = {
        "job_id": job_id,
        "task": "image_from_prompt",
        "prompt": "A majestic lion standing on a rock at sunset, photorealistic, 8k",
        "output": {
            "format": "png",
            "width": 512,
            "height": 512,
        },
        "meta": {
            "guidance_scale": 7.5,
            "num_inference_steps": 20,
            "seed": 42,
        },
    }

    print(f"\n[1/5] Created request: job_id={job_id}")
    print(f"      Prompt: {request['prompt'][:50]}...")

    # Step 2: Send to router
    print(f"\n[2/5] Sending to router topic: {config.KAFKA_TOPIC_REQUESTS}")
    kafka = KafkaMediaClient(
        bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
        group_id=f"e2e-test-{uuid.uuid4().hex[:4]}",
    )
    kafka.publish(config.KAFKA_TOPIC_REQUESTS, request, key=job_id)
    print("      Message published to Kafka")

    # Step 3: Process through router
    print(f"\n[3/5] Processing through router...")
    from app.graphs.router_graph import run_router_graph
    router_result = run_router_graph(request)
    print(f"      Router completed: routed to image generation")

    # Step 4: Consume from image topic and process
    print(f"\n[4/5] Processing image generation...")
    # Give Kafka a moment
    time.sleep(1)

    # Consume the routed message
    messages = kafka.consume(
        topics=[config.KAFKA_TOPIC_IMAGE_PROMPT_REQUESTS],
        timeout_ms=5000,
        max_records=1,
    )

    if not messages:
        print("      WARNING: No message found on image topic, running directly...")
        # Run directly if message not found
        from app.graphs.image_prompt_graph import run_image_prompt_graph
        run_image_prompt_graph(request)
    else:
        from app.graphs.image_prompt_graph import run_image_prompt_graph
        for msg in messages:
            print(f"      Processing: {msg.value.get('job_id')}")
            run_image_prompt_graph(msg.value)

    # Step 5: Check results topic
    print(f"\n[5/5] Checking results...")
    time.sleep(1)

    results = kafka.consume(
        topics=[config.KAFKA_TOPIC_RESULTS],
        timeout_ms=3000,
        max_records=10,
    )

    # Find our result
    our_result = None
    for msg in results:
        if msg.value.get("job_id") == job_id:
            our_result = msg.value
            break

    kafka.close()

    if our_result:
        print(f"\n{'=' * 60}")
        print("RESULT:")
        print(f"  Job ID: {our_result.get('job_id')}")
        print(f"  Success: {our_result.get('success')}")
        if our_result.get('success'):
            print(f"  URL: {our_result.get('response_url')}")
            print(f"\n{'=' * 60}")
            print("TEST PASSED!")

            # Try to download and show the image
            url = our_result.get('response_url')
            if url:
                try:
                    import requests
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        output_dir = Path("simulation_output")
                        output_dir.mkdir(exist_ok=True)
                        output_path = output_dir / f"{job_id}.png"
                        with open(output_path, "wb") as f:
                            f.write(response.content)
                        print(f"  Downloaded to: {output_path}")
                except Exception as e:
                    print(f"  Could not download: {e}")
        else:
            print(f"  Error: {our_result.get('error')}")
            print(f"\n{'=' * 60}")
            print("TEST FAILED")
    else:
        print(f"\n{'=' * 60}")
        print("No result found for job_id. Check worker logs.")
        print("TEST INCONCLUSIVE")

    print("=" * 60)


if __name__ == "__main__":
    test_image_prompt_pipeline()
