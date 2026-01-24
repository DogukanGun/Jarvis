"""
Shared TypedDict definitions for internal data flow.

These types are used for passing data between graph nodes.
"""
from typing import TypedDict, Optional, List, Any
from PIL import Image


class GenerationResult(TypedDict):
    """Result from a model generation."""
    success: bool
    output_path: Optional[str]  # Local file path to generated media
    error: Optional[str]
    metadata: dict  # Generation metadata (seed used, actual dimensions, etc.)


class UploadResult(TypedDict):
    """Result from uploading to storage."""
    success: bool
    url: Optional[str]  # Public URL to uploaded file
    error: Optional[str]
    bucket: str
    key: str


class DownloadResult(TypedDict):
    """Result from downloading a reference image."""
    success: bool
    image: Optional[Any]  # PIL.Image.Image (use Any to avoid import issues)
    error: Optional[str]
    source_url: str


class VideoFrame(TypedDict):
    """Single frame in video generation."""
    index: int
    image: Any  # PIL.Image.Image or numpy array
    timestamp_ms: float


class VideoGenerationResult(TypedDict):
    """Result from video generation."""
    success: bool
    frames: Optional[List[VideoFrame]]
    audio_path: Optional[str]  # Path to generated audio if any
    output_path: Optional[str]  # Final encoded video path
    error: Optional[str]
    metadata: dict
