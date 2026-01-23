"""
State definition for Image Prompt Graph.

Tracks image generation from text prompts.
"""
from typing import TypedDict, Optional, List, Dict, Any


class ImagePromptGraphState(TypedDict, total=False):
    """
    State for the Image Prompt Graph.

    Flow: load_model -> generate -> upload_result -> publish_result
    """
    # ===== INPUT =====
    request: Dict[str, Any]  # Parsed RenderRequest dict
    job_id: str

    # ===== LOAD_MODEL OUTPUT =====
    model_loaded: bool
    model_error: Optional[str]

    # ===== GENERATE OUTPUT =====
    generation_success: bool
    output_path: Optional[str]  # Local file path to generated image
    generation_error: Optional[str]
    generation_metadata: Dict[str, Any]  # seed, dimensions, etc.

    # ===== UPLOAD OUTPUT =====
    upload_success: bool
    response_url: Optional[str]  # Public URL to uploaded file
    upload_error: Optional[str]

    # ===== PUBLISH OUTPUT =====
    result_published: bool

    # ===== ERROR HANDLING =====
    error: Optional[str]
