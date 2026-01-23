"""
Download Source Node.

Downloads the source image to be edited from the provided URL.
"""
import logging
from typing import Dict, Any, Literal
from io import BytesIO

from app.config import config
from app.graphs.image_edit_graph.state import ImageEditGraphState

logger = logging.getLogger(__name__)


def download_source_node(state: ImageEditGraphState) -> Dict[str, Any]:
    """
    Download the source image from URL.

    Args:
        state: Current graph state with request

    Returns:
        State update with source_image
    """
    job_id = state.get("job_id", "unknown")
    request = state.get("request", {})
    image_url = request.get("input_image_url")

    if not image_url:
        logger.error(f"No input_image_url for job {job_id}")
        return {
            "source_downloaded": False,
            "source_error": "No input_image_url provided",
            "error": "No source image URL",
        }

    logger.info(f"Downloading source image for job {job_id} from {image_url}")

    try:
        import requests
        from PIL import Image

        response = requests.get(
            image_url,
            timeout=config.HTTP_TIMEOUT,
            headers={"User-Agent": "ContentCreator/1.0"},
        )
        response.raise_for_status()

        image = Image.open(BytesIO(response.content))

        if image.mode != "RGB":
            image = image.convert("RGB")

        logger.info(
            f"Downloaded source image for job {job_id}: "
            f"{image.size[0]}x{image.size[1]}"
        )

        return {
            "source_downloaded": True,
            "source_image": image,
            "source_error": None,
        }

    except Exception as e:
        logger.error(f"Failed to download source image for job {job_id}: {e}")
        return {
            "source_downloaded": False,
            "source_error": str(e),
            "error": f"Source download failed: {str(e)}",
        }


def download_router(state: ImageEditGraphState) -> Literal["load", "error"]:
    """
    Conditional edge function to decide next node.
    """
    if state.get("source_downloaded"):
        return "load"
    return "error"
