"""
Pytest configuration and fixtures for Content Creator tests.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_image_request():
    """Sample image generation request."""
    return {
        "job_id": "test-job-123",
        "task": "image_from_prompt",
        "prompt": "A beautiful sunset over mountains",
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


@pytest.fixture
def sample_video_request():
    """Sample video generation request (legacy format)."""
    return {
        "job_id": "test-video-456",
        "task": "video_from_prompt",
        "prompt": "A cat playing with a ball",
        "output": {
            "format": "mp4",
            "width": 512,
            "height": 384,
            "duration_s": 4.0,
            "fps": 24,
        },
        "meta": {
            "guidance_scale": 7.5,
            "num_inference_steps": 20,
        },
    }


@pytest.fixture
def sample_ltx2_video_request():
    """Sample LTX-2 video generation request with optimized parameters."""
    return {
        "job_id": "test-ltx2-video-001",
        "task": "video_from_prompt",
        "prompt": "A majestic eagle soaring through clouds at sunset, cinematic lighting",
        "output": {
            "format": "mp4",
            "width": 1024,
            "height": 1024,
            "fps": 24.0,
        },
        "meta": {
            "seed": 42,
            "guidance_scale": 4.0,
            "num_inference_steps": 40,
            "num_frames": 121,
            "negative_prompt": "blurry, low quality, distorted",
        },
    }


@pytest.fixture
def sample_image_edit_request():
    """Sample image edit request."""
    return {
        "job_id": "test-edit-789",
        "task": "edit_image_from_prompt_and_image",
        "prompt": "Make the sky more colorful",
        "input_image_url": "https://example.com/image.png",
        "output": {
            "format": "png",
            "width": 512,
            "height": 512,
        },
        "meta": {},
    }


@pytest.fixture
def mock_kafka_client():
    """Mock Kafka client."""
    mock = MagicMock()
    mock.publish.return_value = True
    mock.consume.return_value = []
    return mock


@pytest.fixture
def mock_storage_client():
    """Mock storage client."""
    mock = MagicMock()
    mock.upload_file.return_value = {
        "success": True,
        "url": "http://localhost:9000/media-renders/test.png",
        "error": None,
        "bucket": "media-renders",
        "key": "renders/2024/01/23/test.png",
    }
    return mock


@pytest.fixture
def mock_image_model():
    """Mock image generation model."""
    from PIL import Image
    import numpy as np

    mock = MagicMock()

    # Create a fake result image
    fake_image = Image.fromarray(np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8))

    result = MagicMock()
    result.images = [fake_image]
    mock.return_value = result

    return mock
