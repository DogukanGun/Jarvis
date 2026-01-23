"""
Pydantic models for Kafka message contracts.

Request and result schemas for the media rendering pipeline.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class TaskType(str, Enum):
    """Supported media generation task types."""
    VIDEO_FROM_PROMPT = "video_from_prompt"
    IMAGE_FROM_PROMPT = "image_from_prompt"
    IMAGE_FROM_PROMPT_AND_IMAGE = "image_from_prompt_and_image"
    EDIT_IMAGE_FROM_PROMPT_AND_IMAGE = "edit_image_from_prompt_and_image"


class OutputFormat(str, Enum):
    """Supported output formats."""
    MP4 = "mp4"
    PNG = "png"
    JPG = "jpg"
    WEBP = "webp"


class OutputConfig(BaseModel):
    """Output configuration for media generation."""
    format: OutputFormat = OutputFormat.PNG
    width: int = Field(default=1024, ge=64, le=4096)
    height: int = Field(default=1024, ge=64, le=4096)
    duration_s: Optional[float] = Field(default=None, ge=1.0, le=60.0)
    fps: Optional[float] = Field(default=None, ge=1.0, le=60.0, description="Frames per second (supports float for LTX-2)")


class MetaConfig(BaseModel):
    """Optional generation metadata/parameters."""
    style: Optional[str] = None
    seed: Optional[int] = None
    guidance_scale: Optional[float] = Field(default=None, ge=1.0, le=20.0)
    num_inference_steps: Optional[int] = Field(default=None, ge=1, le=100)
    negative_prompt: Optional[str] = None
    num_frames: Optional[int] = Field(default=None, ge=1, le=300, description="Number of frames for video generation")


class RenderRequest(BaseModel):
    """
    Request message for media rendering.

    Consumed from media.render.requests topic.
    """
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task: TaskType
    prompt: str = Field(..., min_length=1, max_length=4096)
    input_image_url: Optional[str] = None
    output: OutputConfig = Field(default_factory=OutputConfig)
    meta: MetaConfig = Field(default_factory=MetaConfig)

    def requires_input_image(self) -> bool:
        """Check if this task type requires an input image."""
        return self.task in [
            TaskType.IMAGE_FROM_PROMPT_AND_IMAGE,
            TaskType.EDIT_IMAGE_FROM_PROMPT_AND_IMAGE,
        ]

    def is_video_task(self) -> bool:
        """Check if this is a video generation task."""
        return self.task == TaskType.VIDEO_FROM_PROMPT

    def get_target_topic(self) -> str:
        """Get the target Kafka topic for routing."""
        from app.config import config

        topic_map = {
            TaskType.VIDEO_FROM_PROMPT: config.KAFKA_TOPIC_VIDEO_REQUESTS,
            TaskType.IMAGE_FROM_PROMPT: config.KAFKA_TOPIC_IMAGE_PROMPT_REQUESTS,
            TaskType.IMAGE_FROM_PROMPT_AND_IMAGE: config.KAFKA_TOPIC_IMAGE_REFERENCE_REQUESTS,
            TaskType.EDIT_IMAGE_FROM_PROMPT_AND_IMAGE: config.KAFKA_TOPIC_IMAGE_EDIT_REQUESTS,
        }
        return topic_map[self.task]


class RenderResult(BaseModel):
    """
    Result message for media rendering.

    Published to media.render.results topic.
    """
    job_id: str
    success: bool
    response_url: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def success_result(cls, job_id: str, url: str) -> "RenderResult":
        """Create a successful result."""
        return cls(job_id=job_id, success=True, response_url=url)

    @classmethod
    def error_result(cls, job_id: str, error: str) -> "RenderResult":
        """Create an error result."""
        return cls(job_id=job_id, success=False, error=error)
