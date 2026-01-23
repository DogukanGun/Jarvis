#!/usr/bin/env python3
"""
Media Rendering Pipeline Simulation

Tests all media generation operations by sending requests via Kafka
and listening for results.

Usage:
    # Start infrastructure first
    docker-compose -f docker-compose.dev.yml up -d

    # Start workers (in separate terminals)
    WORKER_TYPE=router python main.py
    WORKER_TYPE=image_prompt python main.py
    WORKER_TYPE=video python main.py

    # Run simulation
    python simulation.py

    # Or run specific tests
    python simulation.py --test image_prompt
    python simulation.py --test video
    python simulation.py --test all
"""
import argparse
import json
import logging
import os
import sys
import time
import uuid
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import config
from app.clients.kafka_client import KafkaMediaClient, ConsumedMessage
from app.schemas.messages import TaskType, OutputFormat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================================
# TEST PROMPTS AND REQUESTS
# ============================================================================

# Optimized for Apple Silicon MPS - smaller sizes for faster generation
IMAGE_PROMPT_TESTS = [
    {
        "name": "Sunset Landscape",
        "prompt": "A breathtaking sunset over snow-capped mountains, golden hour lighting, photorealistic",
        "output": {"format": "png", "width": 512, "height": 512},
        "meta": {"guidance_scale": 7.5, "num_inference_steps": 20, "seed": 42},
    },
    {
        "name": "Cyberpunk City",
        "prompt": "A futuristic cyberpunk cityscape at night, neon lights reflecting on wet streets, flying cars",
        "output": {"format": "png", "width": 512, "height": 512},
        "meta": {"guidance_scale": 8.0, "num_inference_steps": 20, "seed": 123},
    },
]

# Video tests - reduced for faster local testing
VIDEO_PROMPT_TESTS = [
    {
        "name": "Ocean Waves",
        "prompt": "Calm ocean waves gently rolling onto a sandy beach at sunset",
        "output": {"format": "mp4", "width": 256, "height": 256, "duration_s": 2.0, "fps": 8},
        "meta": {"guidance_scale": 7.5, "num_inference_steps": 15, "seed": 42},
    },
]

# Image reference tests - using a simple test image
IMAGE_REFERENCE_TESTS = [
    {
        "name": "Style Transfer",
        "prompt": "Transform into impressionist painting style with vibrant colors",
        "input_image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/300px-PNG_transparency_demonstration_1.png",
        "output": {"format": "png", "width": 512, "height": 512},
        "meta": {"guidance_scale": 7.5, "num_inference_steps": 20},
    },
]

# Image edit tests
IMAGE_EDIT_TESTS = [
    {
        "name": "Add Elements",
        "prompt": "Add colorful flowers and butterflies",
        "input_image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/300px-PNG_transparency_demonstration_1.png",
        "output": {"format": "png", "width": 512, "height": 512},
        "meta": {"guidance_scale": 7.5, "num_inference_steps": 20},
    },
]


# ============================================================================
# RESULT TRACKING
# ============================================================================

@dataclass
class TestResult:
    """Tracks a single test result."""
    job_id: str
    test_name: str
    task_type: str
    sent_at: datetime
    completed_at: Optional[datetime] = None
    success: Optional[bool] = None
    response_url: Optional[str] = None
    error: Optional[str] = None
    local_path: Optional[str] = None


@dataclass
class SimulationResults:
    """Tracks all simulation results."""
    results: Dict[str, TestResult] = field(default_factory=dict)
    output_dir: str = "simulation_output"

    def add_pending(self, job_id: str, test_name: str, task_type: str):
        """Add a pending test."""
        self.results[job_id] = TestResult(
            job_id=job_id,
            test_name=test_name,
            task_type=task_type,
            sent_at=datetime.now(),
        )

    def update_result(self, job_id: str, success: bool, url: str = None, error: str = None):
        """Update a test result."""
        if job_id in self.results:
            result = self.results[job_id]
            result.completed_at = datetime.now()
            result.success = success
            result.response_url = url
            result.error = error

    def set_local_path(self, job_id: str, path: str):
        """Set local file path for downloaded result."""
        if job_id in self.results:
            self.results[job_id].local_path = path

    def get_pending_count(self) -> int:
        """Get count of pending tests."""
        return sum(1 for r in self.results.values() if r.success is None)

    def print_summary(self):
        """Print summary of all results."""
        print("\n" + "=" * 60)
        print("SIMULATION RESULTS SUMMARY")
        print("=" * 60)

        success_count = sum(1 for r in self.results.values() if r.success is True)
        fail_count = sum(1 for r in self.results.values() if r.success is False)
        pending_count = sum(1 for r in self.results.values() if r.success is None)

        print(f"\nTotal: {len(self.results)} | Success: {success_count} | Failed: {fail_count} | Pending: {pending_count}")
        print("-" * 60)

        for job_id, result in self.results.items():
            status = "✓" if result.success else ("✗" if result.success is False else "⏳")
            duration = ""
            if result.completed_at:
                delta = result.completed_at - result.sent_at
                duration = f" ({delta.total_seconds():.1f}s)"

            print(f"{status} [{result.task_type}] {result.test_name}{duration}")
            if result.local_path:
                print(f"   → Saved: {result.local_path}")
            if result.error:
                print(f"   → Error: {result.error}")

        print("=" * 60)


# ============================================================================
# SIMULATION CLASS
# ============================================================================

class MediaPipelineSimulation:
    """
    Simulates the media rendering pipeline by sending requests
    and collecting results.
    """

    def __init__(
        self,
        output_dir: str = "simulation_output",
        timeout_seconds: int = 300,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.timeout_seconds = timeout_seconds

        self.kafka = KafkaMediaClient(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            group_id=f"simulation-{uuid.uuid4().hex[:8]}",
        )

        self.results = SimulationResults(output_dir=str(self.output_dir))
        self._stop_listener = False

    def _build_request(
        self,
        task: TaskType,
        test_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a render request from test config."""
        job_id = f"sim-{uuid.uuid4().hex[:12]}"

        request = {
            "job_id": job_id,
            "task": task.value,
            "prompt": test_config["prompt"],
            "output": test_config.get("output", {}),
            "meta": test_config.get("meta", {}),
        }

        if "input_image_url" in test_config:
            request["input_image_url"] = test_config["input_image_url"]

        return request

    def send_request(self, request: Dict[str, Any], test_name: str):
        """Send a render request to Kafka."""
        job_id = request["job_id"]
        task_type = request["task"]

        logger.info(f"Sending request: {test_name} (job_id={job_id})")

        success = self.kafka.publish(
            topic=config.KAFKA_TOPIC_REQUESTS,
            message=request,
            key=job_id,
        )

        if success:
            self.results.add_pending(job_id, test_name, task_type)
            logger.info(f"Request sent successfully: {job_id}")
        else:
            logger.error(f"Failed to send request: {job_id}")

        return success

    def _download_result(self, job_id: str, url: str) -> Optional[str]:
        """Download result file from URL."""
        try:
            import requests

            # Extract extension from URL
            ext = url.split(".")[-1].split("?")[0]
            if ext not in ["png", "jpg", "jpeg", "mp4", "webm", "webp"]:
                ext = "bin"

            # Download file
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Save to output directory
            result = self.results.results.get(job_id)
            test_name = result.test_name if result else job_id
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in test_name)

            filename = f"{safe_name}_{job_id[:8]}.{ext}"
            filepath = self.output_dir / filename

            with open(filepath, "wb") as f:
                f.write(response.content)

            logger.info(f"Downloaded: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.warning(f"Failed to download result for {job_id}: {e}")
            return None

    def _handle_result(self, msg: ConsumedMessage):
        """Handle a result message."""
        result = msg.value
        job_id = result.get("job_id", "unknown")
        success = result.get("success", False)
        url = result.get("response_url")
        error = result.get("error")

        if success:
            logger.info(f"Received result for {job_id}: SUCCESS - {url}")
        else:
            logger.warning(f"Received result for {job_id}: FAILED - {error}")

        self.results.update_result(job_id, success, url, error)

        # Download result if successful
        if success and url:
            local_path = self._download_result(job_id, url)
            if local_path:
                self.results.set_local_path(job_id, local_path)

    def listen_for_results(self):
        """Listen for results on the results topic."""
        logger.info(f"Starting result listener on {config.KAFKA_TOPIC_RESULTS}")

        while not self._stop_listener:
            try:
                messages = self.kafka.consume(
                    topics=[config.KAFKA_TOPIC_RESULTS],
                    timeout_ms=1000,
                    max_records=10,
                )

                for msg in messages:
                    self._handle_result(msg)

            except Exception as e:
                logger.error(f"Listener error: {e}")
                time.sleep(1)

    def run_tests(
        self,
        test_types: List[str] = None,
        wait_for_results: bool = True,
    ):
        """
        Run simulation tests.

        Args:
            test_types: List of test types to run. Options:
                       ["image_prompt", "video", "image_reference", "image_edit", "all"]
            wait_for_results: Whether to wait for all results
        """
        if test_types is None or "all" in test_types:
            test_types = ["image_prompt", "video", "image_reference", "image_edit"]

        # Start listener thread
        listener_thread = threading.Thread(target=self.listen_for_results, daemon=True)
        listener_thread.start()

        # Give listener time to start
        time.sleep(1)

        # Send test requests
        requests_sent = 0

        if "image_prompt" in test_types:
            logger.info("\n=== Sending Image Prompt Tests ===")
            for test in IMAGE_PROMPT_TESTS:
                request = self._build_request(TaskType.IMAGE_FROM_PROMPT, test)
                if self.send_request(request, test["name"]):
                    requests_sent += 1
                time.sleep(0.5)  # Small delay between requests

        if "video" in test_types:
            logger.info("\n=== Sending Video Tests ===")
            for test in VIDEO_PROMPT_TESTS:
                request = self._build_request(TaskType.VIDEO_FROM_PROMPT, test)
                if self.send_request(request, test["name"]):
                    requests_sent += 1
                time.sleep(0.5)

        if "image_reference" in test_types:
            logger.info("\n=== Sending Image Reference Tests ===")
            for test in IMAGE_REFERENCE_TESTS:
                request = self._build_request(TaskType.IMAGE_FROM_PROMPT_AND_IMAGE, test)
                if self.send_request(request, test["name"]):
                    requests_sent += 1
                time.sleep(0.5)

        if "image_edit" in test_types:
            logger.info("\n=== Sending Image Edit Tests ===")
            for test in IMAGE_EDIT_TESTS:
                request = self._build_request(TaskType.EDIT_IMAGE_FROM_PROMPT_AND_IMAGE, test)
                if self.send_request(request, test["name"]):
                    requests_sent += 1
                time.sleep(0.5)

        logger.info(f"\n=== Sent {requests_sent} requests ===")

        if not wait_for_results:
            logger.info("Not waiting for results (--no-wait specified)")
            return

        # Wait for results
        logger.info(f"\nWaiting for results (timeout: {self.timeout_seconds}s)...")
        start_time = time.time()

        while True:
            pending = self.results.get_pending_count()
            elapsed = time.time() - start_time

            if pending == 0:
                logger.info("All results received!")
                break

            if elapsed > self.timeout_seconds:
                logger.warning(f"Timeout reached with {pending} pending results")
                break

            # Progress update every 10 seconds
            if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                completed = requests_sent - pending
                logger.info(f"Progress: {completed}/{requests_sent} completed, {pending} pending...")

            time.sleep(1)

        # Stop listener
        self._stop_listener = True
        time.sleep(1)

        # Print summary
        self.results.print_summary()

        # Save results to JSON
        self._save_results_json()

    def _save_results_json(self):
        """Save results to a JSON file."""
        output_file = self.output_dir / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        results_data = {
            "timestamp": datetime.now().isoformat(),
            "results": [
                {
                    "job_id": r.job_id,
                    "test_name": r.test_name,
                    "task_type": r.task_type,
                    "sent_at": r.sent_at.isoformat() if r.sent_at else None,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                    "success": r.success,
                    "response_url": r.response_url,
                    "error": r.error,
                    "local_path": r.local_path,
                }
                for r in self.results.results.values()
            ]
        }

        with open(output_file, "w") as f:
            json.dump(results_data, f, indent=2)

        logger.info(f"Results saved to: {output_file}")

    def cleanup(self):
        """Clean up resources."""
        self._stop_listener = True
        self.kafka.close()


# ============================================================================
# QUICK TEST FUNCTIONS
# ============================================================================

def send_single_image_test(prompt: str = None):
    """Send a single image generation test."""
    sim = MediaPipelineSimulation(timeout_seconds=120)

    test = {
        "name": "Quick Image Test",
        "prompt": prompt or "A beautiful mountain landscape at sunset, photorealistic",
        "output": {"format": "png", "width": 512, "height": 512},
        "meta": {"guidance_scale": 7.5, "num_inference_steps": 20},
    }

    request = sim._build_request(TaskType.IMAGE_FROM_PROMPT, test)
    sim.send_request(request, test["name"])

    print(f"\nRequest sent: {request['job_id']}")
    print("Listening for result...")

    sim.run_tests(test_types=[], wait_for_results=True)
    sim.cleanup()


def send_single_video_test(prompt: str = None):
    """Send a single video generation test."""
    sim = MediaPipelineSimulation(timeout_seconds=300)

    test = {
        "name": "Quick Video Test",
        "prompt": prompt or "Ocean waves gently rolling onto a sandy beach",
        "output": {"format": "mp4", "width": 512, "height": 384, "duration_s": 3.0, "fps": 24},
        "meta": {"guidance_scale": 7.5, "num_inference_steps": 20},
    }

    request = sim._build_request(TaskType.VIDEO_FROM_PROMPT, test)
    sim.send_request(request, test["name"])

    print(f"\nRequest sent: {request['job_id']}")
    print("Listening for result...")

    sim.run_tests(test_types=[], wait_for_results=True)
    sim.cleanup()


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Media Rendering Pipeline Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run all tests
    python simulation.py

    # Run specific test types
    python simulation.py --test image_prompt
    python simulation.py --test video
    python simulation.py --test image_prompt video

    # Quick single test
    python simulation.py --quick-image "A cute cat"
    python simulation.py --quick-video "Fireworks in the night sky"

    # Custom output directory
    python simulation.py --output ./my_results

    # Send requests without waiting
    python simulation.py --no-wait
        """
    )

    parser.add_argument(
        "--test",
        nargs="+",
        choices=["all", "image_prompt", "video", "image_reference", "image_edit"],
        default=["all"],
        help="Test types to run",
    )

    parser.add_argument(
        "--output",
        default="simulation_output",
        help="Output directory for downloaded results",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds to wait for results",
    )

    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Send requests without waiting for results",
    )

    parser.add_argument(
        "--quick-image",
        metavar="PROMPT",
        help="Send a single image test with custom prompt",
    )

    parser.add_argument(
        "--quick-video",
        metavar="PROMPT",
        help="Send a single video test with custom prompt",
    )

    args = parser.parse_args()

    # Handle quick tests
    if args.quick_image:
        send_single_image_test(args.quick_image)
        return

    if args.quick_video:
        send_single_video_test(args.quick_video)
        return

    # Run full simulation
    print("=" * 60)
    print("MEDIA RENDERING PIPELINE SIMULATION")
    print("=" * 60)
    print(f"Output directory: {args.output}")
    print(f"Test types: {args.test}")
    print(f"Timeout: {args.timeout}s")
    print(f"Kafka: {config.KAFKA_BOOTSTRAP_SERVERS}")
    print("=" * 60)

    sim = MediaPipelineSimulation(
        output_dir=args.output,
        timeout_seconds=args.timeout,
    )

    try:
        sim.run_tests(
            test_types=args.test,
            wait_for_results=not args.no_wait,
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sim.results.print_summary()
    finally:
        sim.cleanup()


if __name__ == "__main__":
    main()
