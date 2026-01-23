"""
Download Reference Node.

Downloads the reference image from the provided URL.
"""
import logging
from typing import Dict, Any, Literal
from io import BytesIO

from app.config import config
from app.graphs.image_reference_graph.state import ImageReferenceGraphState

logger = logging.getLogger(__name__)


def download_reference_node(state: ImageReferenceGraphState) -> Dict[str, Any]:
    """
    Download the reference image from URL.

    Args:
        state: Current graph state with request

    Returns:
        State update with reference_image
    """
    job_id = state.get("job_id", "unknown")
    request = state.get("request", {})
    image_url = request.get("input_image_url")

    if not image_url:
        logger.error(f"No input_image_url for job {job_id}")
        return {
            "reference_downloaded": False,
            "reference_error": "No input_image_url provided",
            "error": "No reference image URL",
        }

    logger.info(f"Downloading reference image for job {job_id} from {image_url}")

    try:
        import requests
        from PIL import Image

        # Download with timeout
        response = requests.get(
            image_url,
            timeout=config.HTTP_TIMEOUT,
            headers={"User-Agent": "ContentCreator/1.0"},
        )
        response.raise_for_status()

        # Load as PIL Image
        image = Image.open(BytesIO(response.content))

        # Convert to RGB if necessary
        if image.mode != "RGB":
            image = image.convert("RGB")

        logger.info(
            f"Downloaded reference image for job {job_id}: "
            f"{image.size[0]}x{image.size[1]}"
        )

        return {
            "reference_downloaded": True,
            "reference_image": image,
            "reference_error": None,
        }

    except Exception as e:
        logger.error(f"Failed to download reference image for job {job_id}: {e}")
        return {
            "reference_downloaded": False,
            "reference_error": str(e),
            "error": f"Reference download failed: {str(e)}",
        }


def download_router(state: ImageReferenceGraphState) -> Literal["load", "error"]:
    """
    Conditional edge function to decide next node.

    Returns:
        "load" if download succeeded
        "error" if download failed
    """
    if state.get("reference_downloaded"):
        return "load"
    return "error"
