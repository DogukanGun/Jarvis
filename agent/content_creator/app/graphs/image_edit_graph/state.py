"""
State definition for Image Edit Graph.

Tracks image editing from prompts and source images.
"""
from typing import TypedDict, Optional, List, Dict, Any


class ImageEditGraphState(TypedDict, total=False):
    """
    State for the Image Edit Graph.

    Flow: download_source -> load_model -> edit -> upload_result -> publish_result
    """
    # ===== INPUT =====
    request: Dict[str, Any]  # Parsed RenderRequest dict
    job_id: str

    # ===== DOWNLOAD_SOURCE OUTPUT =====
    source_downloaded: bool
    source_image: Optional[Any]  # PIL.Image.Image
    source_error: Optional[str]

    # ===== LOAD_MODEL OUTPUT =====
    model_loaded: bool
    model_error: Optional[str]

    # ===== EDIT OUTPUT =====
    edit_success: bool
    output_path: Optional[str]  # Local file path to edited image
    edit_error: Optional[str]
    edit_metadata: Dict[str, Any]

    # ===== UPLOAD OUTPUT =====
    upload_success: bool
    response_url: Optional[str]
    upload_error: Optional[str]

    # ===== PUBLISH OUTPUT =====
    result_published: bool

    # ===== ERROR HANDLING =====
    error: Optional[str]
