"""
State definition for Video Graph.

Tracks video generation from text prompts.
"""
from typing import TypedDict, Optional, List, Dict, Any


class VideoGraphState(TypedDict, total=False):
    """
    State for the Video Graph.

    Flow: load_model -> generate_frames -> encode_video -> upload_result -> publish_result
    """
    # ===== INPUT =====
    request: Dict[str, Any]  # Parsed RenderRequest dict
    job_id: str

    # ===== LOAD_MODEL OUTPUT =====
    model_loaded: bool
    model_error: Optional[str]

    # ===== GENERATE_FRAMES OUTPUT =====
    generation_success: bool
    frames_path: Optional[str]  # Directory containing frames
    generation_error: Optional[str]
    generation_metadata: Dict[str, Any]

    # ===== ENCODE_VIDEO OUTPUT =====
    encode_success: bool
    output_path: Optional[str]  # Path to encoded video file
    encode_error: Optional[str]

    # ===== UPLOAD OUTPUT =====
    upload_success: bool
    response_url: Optional[str]
    upload_error: Optional[str]

    # ===== PUBLISH OUTPUT =====
    result_published: bool

    # ===== ERROR HANDLING =====
    error: Optional[str]
