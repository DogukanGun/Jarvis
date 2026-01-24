"""
Load Model Node.

Loads the text-to-image model (Qwen-Image-2512).
"""
import logging
from typing import Dict, Any
from app.clients.model_client import get_image_model
from app.graphs.image_prompt_graph.state import ImagePromptGraphState

logger = logging.getLogger(__name__)


def load_model_node(state: ImagePromptGraphState) -> Dict[str, Any]:
    """
    Load the text-to-image model.

    Args:
        state: Current graph state

    Returns:
        State update with model_loaded status
    """
    job_id = state.get("job_id", "unknown")
    logger.info(f"Loading image model for job {job_id}...")

    try:

        # This will load the model if not already loaded
        pipeline = get_image_model()

        if pipeline is None:
            raise RuntimeError("Model pipeline is None")

        logger.info(f"Image model loaded for job {job_id}")
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
