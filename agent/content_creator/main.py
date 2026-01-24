#!/usr/bin/env python3
"""
Content Creator Media Rendering Pipeline - Entry Point

Worker types:
- router: Routes requests to appropriate worker topics
- video: Video generation worker (LTX-2)
- image_prompt: Image generation from prompts (Qwen-Image)
- image_edit: Image editing/reference generation (Qwen-Image-Edit)
"""
import logging
import sys
import signal
from typing import Callable

from app.config import config
from app.clients.kafka_client import get_kafka_client, ConsumedMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def handle_router_message(msg: ConsumedMessage):
    """Handle message for router worker."""
    from app.graphs.router_graph import run_router_graph
    run_router_graph(msg.value)


def handle_video_message(msg: ConsumedMessage):
    """Handle message for video worker."""
    from app.graphs.video_graph import run_video_graph
    run_video_graph(msg.value)


def handle_image_prompt_message(msg: ConsumedMessage):
    """Handle message for image prompt worker."""
    from app.graphs.image_prompt_graph import run_image_prompt_graph
    run_image_prompt_graph(msg.value)


def handle_image_reference_message(msg: ConsumedMessage):
    """Handle message for image reference worker."""
    from app.graphs.image_reference_graph import run_image_reference_graph
    run_image_reference_graph(msg.value)


def handle_image_edit_message(msg: ConsumedMessage):
    """Handle message for image edit worker."""
    from app.graphs.image_edit_graph import run_image_edit_graph
    run_image_edit_graph(msg.value)


WORKER_CONFIG = {
    "router": {
        "topics": [config.KAFKA_TOPIC_REQUESTS],
        "handler": handle_router_message,
        "description": "Content Router - Routes requests to workers",
    },
    "video": {
        "topics": [config.KAFKA_TOPIC_VIDEO_REQUESTS],
        "handler": handle_video_message,
        "description": "Video Generator - LTX-2 video generation",
    },
    "image_prompt": {
        "topics": [config.KAFKA_TOPIC_IMAGE_PROMPT_REQUESTS],
        "handler": handle_image_prompt_message,
        "description": "Image Generator - Text-to-image generation",
    },
    "image_reference": {
        "topics": [config.KAFKA_TOPIC_IMAGE_REFERENCE_REQUESTS],
        "handler": handle_image_reference_message,
        "description": "Image Reference - Image generation with reference",
    },
    "image_edit": {
        "topics": [config.KAFKA_TOPIC_IMAGE_EDIT_REQUESTS],
        "handler": handle_image_edit_message,
        "description": "Image Editor - Image editing with prompts",
    },
}


def run_worker(worker_type: str):
    """
    Run the specified worker type.

    Args:
        worker_type: Type of worker to run
    """
    if worker_type not in WORKER_CONFIG:
        print(f"Unknown worker type: {worker_type}")
        print(f"Available types: {', '.join(WORKER_CONFIG.keys())}")
        sys.exit(1)

    worker = WORKER_CONFIG[worker_type]
    logger.info(f"Starting {worker['description']}...")
    logger.info(f"Subscribing to topics: {worker['topics']}")

    # Set up signal handlers for graceful shutdown
    shutdown_requested = False

    def signal_handler(sig, frame):
        nonlocal shutdown_requested
        if shutdown_requested:
            logger.warning("Force shutdown requested")
            sys.exit(1)
        logger.info("Shutdown requested, finishing current work...")
        shutdown_requested = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Get Kafka client with worker-specific group ID
    from app.clients.kafka_client import KafkaMediaClient
    worker_group_id = f"content-creator-{worker_type}"
    kafka = KafkaMediaClient(
        bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
        group_id=worker_group_id,
    )
    logger.info(f"Using Kafka consumer group: {worker_group_id}")

    try:
        logger.info(f"{worker_type} worker ready")

        while not shutdown_requested:
            messages = kafka.consume(
                topics=worker['topics'],
                timeout_ms=1000,
                max_records=1,
            )

            for msg in messages:
                try:
                    job_id = msg.value.get("job_id", "unknown")
                    logger.info(f"Processing job {job_id}")
                    worker['handler'](msg)
                    logger.info(f"Completed job {job_id}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        kafka.close()
        logger.info(f"{worker_type} worker stopped")


def main():
    """Main entry point."""
    worker_type = config.WORKER_TYPE

    if len(sys.argv) > 1:
        worker_type = sys.argv[1]

    if worker_type in ["--help", "-h"]:
        print("Content Creator Media Rendering Pipeline")
        print("=" * 45)
        print("\nUsage: python main.py [worker_type]")
        print("\nWorker types:")
        for name, cfg in WORKER_CONFIG.items():
            print(f"  {name:15} - {cfg['description']}")
        print("\nSet WORKER_TYPE environment variable or pass as argument.")
        return

    run_worker(worker_type)


if __name__ == "__main__":
    main()
