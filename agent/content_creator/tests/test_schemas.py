"""Tests for Pydantic schemas."""
import pytest
from pydantic import ValidationError

from app.schemas.messages import (
    RenderRequest,
    RenderResult,
    TaskType,
    OutputFormat,
    OutputConfig,
    MetaConfig,
)


class TestRenderRequest:
    """Tests for RenderRequest schema."""

    def test_valid_image_request(self, sample_image_request):
        """Test valid image generation request."""
        request = RenderRequest(**sample_image_request)

        assert request.job_id == "test-job-123"
        assert request.task == TaskType.IMAGE_FROM_PROMPT
        assert request.prompt == "A beautiful sunset over mountains"
        assert request.output.width == 512
        assert request.output.height == 512
        assert request.meta.seed == 42

    def test_valid_video_request(self, sample_video_request):
        """Test valid video generation request."""
        request = RenderRequest(**sample_video_request)

        assert request.task == TaskType.VIDEO_FROM_PROMPT
        assert request.output.format == OutputFormat.MP4
        assert request.output.duration_s == 4.0

    def test_requires_input_image(self, sample_image_edit_request):
        """Test requires_input_image method."""
        request = RenderRequest(**sample_image_edit_request)
        assert request.requires_input_image() is True

        # Test task that doesn't require input image
        request2 = RenderRequest(
            task=TaskType.IMAGE_FROM_PROMPT,
            prompt="test",
        )
        assert request2.requires_input_image() is False

    def test_is_video_task(self, sample_video_request, sample_image_request):
        """Test is_video_task method."""
        video_request = RenderRequest(**sample_video_request)
        assert video_request.is_video_task() is True

        image_request = RenderRequest(**sample_image_request)
        assert image_request.is_video_task() is False

    def test_auto_generate_job_id(self):
        """Test that job_id is auto-generated if not provided."""
        request = RenderRequest(
            task=TaskType.IMAGE_FROM_PROMPT,
            prompt="test prompt",
        )
        assert request.job_id is not None
        assert len(request.job_id) > 0

    def test_invalid_prompt_empty(self):
        """Test validation fails for empty prompt."""
        with pytest.raises(ValidationError):
            RenderRequest(
                task=TaskType.IMAGE_FROM_PROMPT,
                prompt="",
            )

    def test_invalid_dimensions(self):
        """Test validation fails for invalid dimensions."""
        with pytest.raises(ValidationError):
            RenderRequest(
                task=TaskType.IMAGE_FROM_PROMPT,
                prompt="test",
                output=OutputConfig(width=10, height=10),  # Too small
            )

    def test_get_target_topic(self, sample_image_request, sample_video_request):
        """Test topic routing."""
        image_request = RenderRequest(**sample_image_request)
        assert "image.prompt" in image_request.get_target_topic()

        video_request = RenderRequest(**sample_video_request)
        assert "video" in video_request.get_target_topic()


class TestRenderResult:
    """Tests for RenderResult schema."""

    def test_success_result(self):
        """Test creating success result."""
        result = RenderResult.success_result(
            job_id="test-123",
            url="http://example.com/result.png",
        )

        assert result.job_id == "test-123"
        assert result.success is True
        assert result.response_url == "http://example.com/result.png"
        assert result.error is None

    def test_error_result(self):
        """Test creating error result."""
        result = RenderResult.error_result(
            job_id="test-123",
            error="Generation failed",
        )

        assert result.job_id == "test-123"
        assert result.success is False
        assert result.response_url is None
        assert result.error == "Generation failed"
