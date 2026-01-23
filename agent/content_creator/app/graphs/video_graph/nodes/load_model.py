"""
Load Model Node.

Loads the LTX-2 video generation model.
"""
import logging
from typing import Dict, Any

from app.graphs.video_graph.state import VideoGraphState

logger = logging.getLogger(__name__)


def load_model_node(state: VideoGraphState) -> Dict[str, Any]:
    """
    Load the video generation model.

    Args:
        state: Current graph state

    Returns:
        State update with model_loaded status
    """
    job_id = state.get("job_id", "unknown")
    logger.info(f"Loading video model for job {job_id}...")

    try:
        from app.clients.model_client import get_video_model

        pipeline = get_video_model()

        if pipeline is None:
            raise RuntimeError("Model pipeline is None")

        logger.info(f"Video model loaded for job {job_id}")
        return {
            "model_loaded": True,
            "model_error": None,
        }

    except Exception as e:
        logger.error(f"Failed to load video model for job {job_id}: {e}")
        return {
            "model_loaded": False,
            "model_error": str(e),
            "error": f"Model loading failed: {str(e)}",
        }
