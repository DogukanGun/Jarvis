"""
State definition for Image Reference Graph.

Tracks image generation from prompts with reference images.
"""
from typing import TypedDict, Optional, List, Dict, Any


class ImageReferenceGraphState(TypedDict, total=False):
    """
    State for the Image Reference Graph.

    Flow: download_reference -> load_model -> generate -> upload_result -> publish_result
    """
    # ===== INPUT =====
    request: Dict[str, Any]  # Parsed RenderRequest dict
    job_id: str

    # ===== DOWNLOAD_REFERENCE OUTPUT =====
    reference_downloaded: bool
    reference_image: Optional[Any]  # PIL.Image.Image
    reference_error: Optional[str]

    # ===== LOAD_MODEL OUTPUT =====
    model_loaded: bool
    model_error: Optional[str]

    # ===== GENERATE OUTPUT =====
    generation_success: bool
    output_path: Optional[str]  # Local file path to generated image
    generation_error: Optional[str]
    generation_metadata: Dict[str, Any]

    # ===== UPLOAD OUTPUT =====
    upload_success: bool
    response_url: Optional[str]
    upload_error: Optional[str]

    # ===== PUBLISH OUTPUT =====
    result_published: bool

    # ===== ERROR HANDLING =====
    error: Optional[str]
