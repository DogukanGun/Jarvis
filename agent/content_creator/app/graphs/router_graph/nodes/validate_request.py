"""
Validate Request Node.

Validates incoming render requests against the schema.
"""
import logging
from typing import Dict, Any

from pydantic import ValidationError

from app.schemas.messages import RenderRequest
from app.graphs.router_graph.state import RouterGraphState

logger = logging.getLogger(__name__)


def validate_request_node(state: RouterGraphState) -> Dict[str, Any]:
    """
    Validate the incoming request message.

    Args:
        state: Current graph state with raw_message

    Returns:
        State update with validation result
    """
    logger.info("Validating request...")

    raw_message = state.get("raw_message", {})
    errors = []

    # Extract job_id early for error responses
    job_id = raw_message.get("job_id")

    try:
        # Validate against Pydantic model
        request = RenderRequest(**raw_message)

        # Additional validation: check if input_image_url is present when required
        if request.requires_input_image() and not request.input_image_url:
            errors.append(
                f"Task '{request.task.value}' requires 'input_image_url' to be provided"
            )

        # Video format validation
        if request.is_video_task():
            if request.output.format.value not in ["mp4", "webm"]:
                errors.append(
                    f"Video task requires video format (mp4/webm), got '{request.output.format.value}'"
                )
            if request.output.duration_s is None:
                errors.append("Video task requires 'output.duration_s' to be specified")

        if errors:
            logger.warning(f"Validation failed for job {job_id}: {errors}")
            return {
                "is_valid": False,
                "validation_errors": errors,
                "request": None,
                "job_id": job_id,
            }

        logger.info(f"Request validated successfully: job_id={request.job_id}, task={request.task.value}")
        return {
            "is_valid": True,
            "validation_errors": [],
            "request": request.model_dump(),
            "job_id": request.job_id,
        }

    except ValidationError as e:
        # Extract error messages from Pydantic
        for error in e.errors():
            loc = ".".join(str(l) for l in error["loc"])
            msg = error["msg"]
            errors.append(f"{loc}: {msg}")

        logger.warning(f"Validation failed for job {job_id}: {errors}")
        return {
            "is_valid": False,
            "validation_errors": errors,
            "request": None,
            "job_id": job_id,
        }

    except Exception as e:
        logger.error(f"Unexpected validation error: {e}")
        return {
            "is_valid": False,
            "validation_errors": [f"Unexpected error: {str(e)}"],
            "request": None,
            "job_id": job_id,
        }
