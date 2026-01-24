#!/usr/bin/env python3
"""
Mock Worker for Pipeline Testing

Processes media render requests without actual model inference.
Generates placeholder images/videos for end-to-end testing.

Usage:
    # Start infrastructure
    docker-compose -f docker-compose.dev.yml up -d

    # Run mock worker (processes ALL task types)
    python mock_worker.py

    # Then run simulation
    python simulation.py
"""
import logging
import signal
import sys
import time
import tempfile
import os
from pathlib import Path
from typing import Dict, Any

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import config
from app.clients.kafka_client import get_kafka_client, ConsumedMessage
from app.clients.storage_client import get_storage_client
from app.schemas.messages import RenderRequest, RenderResult, TaskType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_mock_image(width: int, height: int, text: str) -> bytes:
    """Create a mock image with text."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io

        # Create gradient background
        img = Image.new('RGB', (width, height))
        pixels = img.load()

        for y in range(height):
            for x in range(width):
                r = int(100 + (x / width) * 100)
                g = int(50 + (y / height) * 150)
                b = int(150 - (x / width) * 50)
                pixels[x, y] = (r, g, b)

        # Add text
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        except:
            font = ImageFont.load_default()

        # Draw text with background
        lines = text.split('\n')
        y_offset = height // 3
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            draw.rectangle([x - 5, y_offset - 5, x + text_width + 5, y_offset + 25], fill=(0, 0, 0, 128))
            draw.text((x, y_offset), line, fill=(255, 255, 255), font=font)
            y_offset += 30

        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    except ImportError:
        # If PIL not available, return minimal PNG
        logger.warning("PIL not available, creating minimal placeholder")
        # Minimal 1x1 PNG
        return bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0x0F, 0x00, 0x00,
            0x01, 0x01, 0x00, 0x05, 0x1B, 0xA4, 0x5A, 0x77,
            0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,
            0xAE, 0x42, 0x60, 0x82
        ])


def create_mock_video(width: int, height: int, duration_s: float, fps: int, text: str) -> bytes:
    """Create a mock video file."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io

        # Try to use imageio for video creation
        try:
            import imageio
            import numpy as np

            num_frames = int(duration_s * fps)
            frames = []

            for i in range(num_frames):
                # Create frame with moving gradient
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                offset = int((i / num_frames) * width)

                for y in range(height):
                    for x in range(width):
                        r = int(100 + ((x + offset) % width / width) * 100)
                        g = int(50 + (y / height) * 150)
                        b = int(150 - ((x + offset) % width / width) * 50)
                        frame[y, x] = [r, g, b]

                frames.append(frame)

            # Write to temp file
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            imageio.mimwrite(temp_file.name, frames, fps=fps)

            with open(temp_file.name, 'rb') as f:
                video_bytes = f.read()

            os.unlink(temp_file.name)
            return video_bytes

        except ImportError:
            logger.warning("imageio not available for video, returning placeholder")
            # Return a minimal mp4 placeholder (just header indicating it's a mock)
            return b'MOCK_VIDEO_FILE_' + text.encode()[:100]

    except Exception as e:
        logger.error(f"Error creating mock video: {e}")
        return b'MOCK_VIDEO_FILE'


def process_request(request_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a render request with mock generation.

    Returns result dict with success/error.
    """
    try:
        request = RenderRequest(**request_dict)
        job_id = request.job_id
        task_type = request.task

        logger.info(f"Processing {task_type.value} request: {job_id}")
        logger.info(f"  Prompt: {request.prompt[:80]}...")

        # Simulate processing time
        time.sleep(0.5)

        # Get output config
        width = request.output.width
        height = request.output.height
        output_format = request.output.format.value

        # Create mock output
        text_lines = [
            f"MOCK {task_type.value.upper()}",
            f"Job: {job_id[:12]}",
            f"Size: {width}x{height}",
            f"Prompt: {request.prompt[:40]}..."
        ]
        text = '\n'.join(text_lines)

        if request.is_video_task():
            duration = request.output.duration_s or 3.0
            fps = request.output.fps or 24
            data = create_mock_video(width, height, duration, fps, text)
            output_format = "mp4"
        else:
            data = create_mock_image(width, height, text)
            output_format = "png"

        # Upload to storage
        storage = get_storage_client()
        result = storage.upload_bytes(
            data=data,
            job_id=job_id,
            extension=output_format,
        )

        if result["success"]:
            logger.info(f"Uploaded mock result: {result['url']}")
            return {
                "job_id": job_id,
                "success": True,
                "response_url": result["url"],
                "error": None,
            }
        else:
            logger.error(f"Upload failed: {result['error']}")
            return {
                "job_id": job_id,
                "success": False,
                "response_url": None,
                "error": f"Upload failed: {result['error']}",
            }

    except Exception as e:
        logger.error(f"Processing error: {e}")
        return {
            "job_id": request_dict.get("job_id", "unknown"),
            "success": False,
            "response_url": None,
            "error": str(e),
        }


def run_mock_worker():
    """Run the mock worker that processes all task types."""
    logger.info("Starting Mock Worker")
    logger.info("=" * 50)
    logger.info("This worker processes ALL task types with mock generation")
    logger.info("No GPU or models required - generates placeholder images/videos")
    logger.info("=" * 50)

    # Topics to consume from (all worker topics)
    topics = [
        config.KAFKA_TOPIC_IMAGE_PROMPT_REQUESTS,
        config.KAFKA_TOPIC_VIDEO_REQUESTS,
        config.KAFKA_TOPIC_IMAGE_REFERENCE_REQUESTS,
        config.KAFKA_TOPIC_IMAGE_EDIT_REQUESTS,
    ]

    logger.info(f"Subscribing to topics: {topics}")

    kafka = get_kafka_client()
    shutdown_requested = False

    def signal_handler(sig, frame):
        nonlocal shutdown_requested
        logger.info("Shutdown requested...")
        shutdown_requested = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Mock worker ready - waiting for requests...")

    try:
        while not shutdown_requested:
            messages = kafka.consume(
                topics=topics,
                timeout_ms=1000,
                max_records=1,
            )

            for msg in messages:
                job_id = msg.value.get("job_id", "unknown")
                logger.info(f"Received request: {job_id} from {msg.topic}")

                # Process request
                result = process_request(msg.value)

                # Publish result
                kafka.publish(
                    topic=config.KAFKA_TOPIC_RESULTS,
                    message=result,
                    key=job_id,
                )

                status = "SUCCESS" if result["success"] else "FAILED"
                logger.info(f"Published result for {job_id}: {status}")

    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        kafka.close()
        logger.info("Mock worker stopped")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Mock Worker for Pipeline Testing")
    parser.add_argument(
        "--router",
        action="store_true",
        help="Also run the router (processes media.render.requests)",
    )
    args = parser.parse_args()

    if args.router:
        # Run router + mock worker together
        import threading

        def run_router():
            from main import run_worker
            run_worker("router")

        router_thread = threading.Thread(target=run_router, daemon=True)
        router_thread.start()
        logger.info("Router started in background")
        time.sleep(2)

    run_mock_worker()


if __name__ == "__main__":
    main()
