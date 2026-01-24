"""
Load Model Node.

Loads the image-to-image model (Qwen-Image-Edit-2511).
"""
import logging
from typing import Dict, Any

from app.graphs.image_reference_graph.state import ImageReferenceGraphState

logger = logging.getLogger(__name__)


def load_model_node(state: ImageReferenceGraphState) -> Dict[str, Any]:
    """
    Load the image-to-image model.

    Args:
        state: Current graph state

    Returns:
        State update with model_loaded status
    """
    job_id = state.get("job_id", "unknown")
    logger.info(f"Loading image edit model for job {job_id}...")

    try:
        from app.clients.model_client import get_image_edit_model

        # This will load the model if not already loaded
        pipeline = get_image_edit_model()

        if pipeline is None:
            raise RuntimeError("Model pipeline is None")

        logger.info(f"Image edit model loaded for job {job_id}")
        return {
            "model_loaded": True,
            "model_error": None,
        }

    except Exception as e:
        logger.error(f"Failed to load model for job {job_id}: {e}")
        return {
            "model_loaded": False,
            "model_error": str(e),
            "error": f"Model loading failed: {str(e)}",
        }
