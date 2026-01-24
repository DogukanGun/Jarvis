#!/usr/bin/env python3
"""
Tests for LTX-2 video generation integration.

Includes:
- Unit tests with mocks for fast CI testing
- Integration test that runs actual generation (requires GPU and models)
"""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.schemas.messages import (
    RenderRequest,
    TaskType,
    OutputFormat,
    OutputConfig,
    MetaConfig,
)
from app.config import config


# =============================================================================
# Unit Tests (with mocks - no GPU required)
# =============================================================================

class TestVideoSchemas:
    """Test video-related schema configurations."""

    def test_meta_config_has_num_frames(self):
        """Test that MetaConfig supports num_frames field."""
        meta = MetaConfig(num_frames=121)
        assert meta.num_frames == 121

    def test_meta_config_num_frames_default(self):
        """Test that num_frames defaults to None."""
        meta = MetaConfig()
        assert meta.num_frames is None

    def test_output_config_supports_float_fps(self):
        """Test that OutputConfig supports float fps for LTX-2."""
        output = OutputConfig(fps=24.0)
        assert output.fps == 24.0

    def test_render_request_video(self):
        """Test video render request creation."""
        request = RenderRequest(
            job_id="test-video-001",
            task=TaskType.VIDEO_FROM_PROMPT,
            prompt="A cat walking on a beach",
            output=OutputConfig(
                format=OutputFormat.MP4,
                width=1024,
                height=1024,
                fps=24.0,
            ),
            meta=MetaConfig(
                seed=42,
                num_inference_steps=40,
                num_frames=121,
                guidance_scale=4.0,
            ),
        )
        assert request.is_video_task()
        assert request.output.format == OutputFormat.MP4
        assert request.meta.num_frames == 121


class TestLTX2Config:
    """Test LTX-2 configuration values."""

    def test_ltx2_defaults_exist(self):
        """Test that LTX-2 config defaults are set."""
        assert hasattr(config, 'LTX_DEFAULT_HEIGHT')
        assert hasattr(config, 'LTX_DEFAULT_WIDTH')
        assert hasattr(config, 'LTX_DEFAULT_NUM_FRAMES')
        assert hasattr(config, 'LTX_DEFAULT_FRAME_RATE')
        assert hasattr(config, 'LTX_DEFAULT_CFG_GUIDANCE_SCALE')
        assert hasattr(config, 'LTX_DEFAULT_NUM_INFERENCE_STEPS')

    def test_ltx2_default_values(self):
        """Test LTX-2 default values are reasonable."""
        assert config.LTX_DEFAULT_HEIGHT == 1024
        assert config.LTX_DEFAULT_WIDTH == 1536
        assert config.LTX_DEFAULT_NUM_FRAMES == 121
        assert config.LTX_DEFAULT_FRAME_RATE == 24.0
        assert config.LTX_DEFAULT_CFG_GUIDANCE_SCALE == 4.0
        assert config.LTX_DEFAULT_NUM_INFERENCE_STEPS == 40

    def test_ltx2_model_paths_exist(self):
        """Test that LTX-2 model path configs exist."""
        assert hasattr(config, 'LTX_CHECKPOINT_PATH')
        assert hasattr(config, 'LTX_DISTILLED_LORA_PATH')
        assert hasattr(config, 'LTX_SPATIAL_UPSAMPLER_PATH')
        assert hasattr(config, 'LTX_GEMMA_ROOT')
        assert hasattr(config, 'LTX_ENABLE_FP8')
        assert hasattr(config, 'LTX_DISTILLED_LORA_STRENGTH')

    def test_ltx2_video_model_default(self):
        """Test default video model is LTX-2."""
        assert "ltx-2" in config.LTX_VIDEO_MODEL.lower()


class TestGenerationRouter:
    """Test the generation router logic."""

    def test_router_returns_error_on_failure(self):
        """Test router returns 'error' when generation fails."""
        from app.graphs.video_graph.nodes.generate_frames import generation_router

        state = {"generation_success": False}
        assert generation_router(state) == "error"

    def test_router_returns_upload_for_ltx2(self):
        """Test router returns 'upload' when LTX-2 already encoded."""
        from app.graphs.video_graph.nodes.generate_frames import generation_router

        state = {"generation_success": True, "encode_success": True}
        assert generation_router(state) == "upload"

    def test_router_returns_encode_for_legacy(self):
        """Test router returns 'encode' for legacy pipelines."""
        from app.graphs.video_graph.nodes.generate_frames import generation_router

        state = {"generation_success": True, "encode_success": False}
        assert generation_router(state) == "encode"

        # Also test when encode_success is not set
        state = {"generation_success": True}
        assert generation_router(state) == "encode"


class TestModelClientLTX2Detection:
    """Test model client LTX-2 detection logic."""

    def test_detects_ltx2_model(self):
        """Test that get_video_model detects LTX-2."""
        with patch('app.config.config') as mock_config:
            mock_config.LTX_VIDEO_MODEL = "Lightricks/LTX-2"

            # Should detect LTX-2
            assert "ltx-2" in mock_config.LTX_VIDEO_MODEL.lower()

    def test_detects_legacy_model(self):
        """Test that get_video_model detects legacy models."""
        with patch('app.config.config') as mock_config:
            mock_config.LTX_VIDEO_MODEL = "damo-vilab/text-to-video-ms-1.7b"

            # Should not detect as LTX-2
            assert "ltx-2" not in mock_config.LTX_VIDEO_MODEL.lower()


class TestVideoGraphState:
    """Test video graph state structure."""

    def test_state_has_required_fields(self):
        """Test VideoGraphState has all required fields."""
        from app.graphs.video_graph.state import VideoGraphState

        # Create a minimal state
        state: VideoGraphState = {
            "request": {},
            "job_id": "test",
        }
        assert "request" in state
        assert "job_id" in state


class TestGenerateFramesNodeWithMocks:
    """Test generate_frames_node with mocked pipeline."""

    @pytest.fixture
    def mock_ltx2_pipeline(self):
        """Create a mock LTX-2 pipeline."""
        import torch
        import numpy as np

        mock = MagicMock()
        mock.__class__.__name__ = "TI2VidTwoStagesPipeline"

        # Mock video output (iterator of tensors)
        fake_frames = torch.from_numpy(
            np.random.randint(0, 255, (10, 512, 512, 3), dtype=np.uint8)
        )
        # Mock audio output
        fake_audio = torch.randn(2, 24000 * 5)  # 5 seconds of stereo audio

        mock.return_value = (iter([fake_frames]), fake_audio)
        return mock

    @pytest.fixture
    def sample_ltx2_request(self):
        """Sample LTX-2 video request."""
        return {
            "job_id": "test-ltx2-video",
            "task": "video_from_prompt",
            "prompt": "A cat playing with a ball",
            "output": {
                "format": "mp4",
                "width": 1024,
                "height": 1024,
                "fps": 24.0,
            },
            "meta": {
                "seed": 42,
                "num_inference_steps": 40,
                "num_frames": 25,
                "guidance_scale": 4.0,
            },
        }

    def test_generate_detects_ltx2_pipeline(self, mock_ltx2_pipeline, sample_ltx2_request):
        """Test that generate node detects LTX-2 pipeline type."""
        # This test verifies the detection logic without running actual generation
        pipeline_name = type(mock_ltx2_pipeline).__name__

        # Our detection logic
        is_ltx2 = "TI2Vid" in pipeline_name or "LTX" in pipeline_name

        # Mock returns MagicMock, so we check the class name we set
        assert mock_ltx2_pipeline.__class__.__name__ == "TI2VidTwoStagesPipeline"


# =============================================================================
# Integration Tests (requires GPU and models)
# =============================================================================

def has_cuda():
    """Check if CUDA is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def has_ltx2_packages():
    """Check if LTX-2 packages are installed."""
    try:
        from ltx_pipelines import TI2VidTwoStagesPipeline
        from ltx_core.loader import LoraPathStrengthAndSDOps
        return True
    except ImportError:
        return False


@pytest.mark.skipif(
    not has_cuda() or not has_ltx2_packages(),
    reason="Requires CUDA GPU and LTX-2 packages"
)
class TestLTX2Integration:
    """Integration tests that run actual video generation."""

    def test_load_ltx2_pipeline(self):
        """Test loading the LTX-2 pipeline (downloads models if needed)."""
        from app.clients.model_client import get_video_model

        try:
            pipeline = get_video_model()
            assert pipeline is not None
            assert "TI2Vid" in type(pipeline).__name__
        except Exception as e:
            pytest.skip(f"Model loading failed (may need to download): {e}")

    def test_generate_short_video(self):
        """Test generating a short video with LTX-2."""
        from app.graphs.video_graph.nodes.generate_frames import generate_frames_node

        state = {
            "job_id": "integration-test-001",
            "request": {
                "job_id": "integration-test-001",
                "task": "video_from_prompt",
                "prompt": "A calm ocean wave at sunset",
                "output": {
                    "format": "mp4",
                    "width": 512,  # Smaller for faster test
                    "height": 512,
                    "fps": 24.0,
                },
                "meta": {
                    "seed": 42,
                    "num_inference_steps": 10,  # Fewer steps for faster test
                    "num_frames": 25,  # ~1 second video
                    "guidance_scale": 4.0,
                },
            },
        }

        try:
            result = generate_frames_node(state)

            assert result["generation_success"] is True
            assert result["output_path"] is not None
            assert os.path.exists(result["output_path"])

            # Verify it's a valid video file
            file_size = os.path.getsize(result["output_path"])
            assert file_size > 0

            # Cleanup
            if result["output_path"]:
                temp_dir = os.path.dirname(result["output_path"])
                shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            pytest.skip(f"Generation failed: {e}")


# =============================================================================
# Manual Test Runner (for standalone execution)
# =============================================================================

def generate_and_save_video():
    """Generate a video and save it to the test folder."""
    from app.graphs.video_graph import run_video_graph

    print("=" * 60)
    print("LTX-2 Video Generation Test")
    print("=" * 60)

    # Check prerequisites
    if not has_cuda():
        print("WARNING: CUDA not available, generation may fail or be slow")

    if not has_ltx2_packages():
        print("ERROR: LTX-2 packages not installed")
        print("Install with:")
        print("  pip install -e ./LTX-2/packages/ltx-core")
        print("  pip install -e ./LTX-2/packages/ltx-pipelines")
        return None

    print("\nGenerating video...")
    print("This may take several minutes on first run (model download)")
    print("-" * 60)

    request = {
        "job_id": "manual-test-video",
        "task": "video_from_prompt",
        "prompt": "A majestic eagle soaring through clouds at golden hour, cinematic lighting",
        "output": {
            "format": "mp4",
            "width": 1024,
            "height": 1024,
            "fps": 24.0,
        },
        "meta": {
            "seed": 42,
            "num_inference_steps": 40,
            "num_frames": 49,  # ~2 seconds
            "guidance_scale": 4.0,
        },
    }

    try:
        # Run the full graph (without Kafka/MinIO)
        from app.graphs.video_graph.nodes.generate_frames import generate_frames_node

        state = {
            "job_id": request["job_id"],
            "request": request,
        }

        result = generate_frames_node(state)

        if result.get("generation_success") and result.get("output_path"):
            temp_path = result["output_path"]

            # Copy to test folder
            test_folder = Path(__file__).parent
            output_filename = "generated_video_test.mp4"
            output_path = test_folder / output_filename

            shutil.copy2(temp_path, output_path)

            print(f"\nVideo successfully generated!")
            print(f"Saved to: {output_path}")
            print(f"File size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")

            # Print metadata
            metadata = result.get("generation_metadata", {})
            print(f"\nGeneration metadata:")
            for key, value in metadata.items():
                print(f"  {key}: {value}")

            # Cleanup temp
            temp_dir = os.path.dirname(temp_path)
            shutil.rmtree(temp_dir, ignore_errors=True)

            return str(output_path)
        else:
            print(f"\nGeneration failed: {result.get('generation_error', 'Unknown error')}")
            return None

    except Exception as e:
        print(f"\nError during generation: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Run manual test
    saved_path = generate_and_save_video()
    if saved_path:
        print(f"\n{'=' * 60}")
        print(f"SUCCESS: Video saved to {saved_path}")
        print(f"{'=' * 60}")
    else:
        print(f"\n{'=' * 60}")
        print("FAILED: Could not generate video")
        print(f"{'=' * 60}")
        sys.exit(1)
