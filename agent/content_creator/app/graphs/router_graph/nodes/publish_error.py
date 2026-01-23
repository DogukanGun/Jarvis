"""
Publish Error Node.

Publishes error result when request validation fails.
"""
import logging
from typing import Dict, Any

from app.clients.kafka_client import get_kafka_client
from app.schemas.messages import RenderResult
from app.config import config
from app.graphs.router_graph.state import RouterGraphState

logger = logging.getLogger(__name__)


def publish_error_node(state: RouterGraphState) -> Dict[str, Any]:
    """
    Publish an error result for invalid requests.

    Args:
        state: Current graph state with validation_errors

    Returns:
        State update with result_published
    """
    job_id = state.get("job_id") or "unknown"
    validation_errors = state.get("validation_errors", [])
    error = state.get("error")

    # Build error message
    if validation_errors:
        error_msg = "Validation failed: " + "; ".join(validation_errors)
    elif error:
        error_msg = error
    else:
        error_msg = "Unknown routing error"

    logger.warning(f"Publishing error result for job {job_id}: {error_msg}")

    try:
        # Create error result
        result = RenderResult.error_result(job_id=job_id, error=error_msg)

        # Publish to results topic
        kafka = get_kafka_client()
        success = kafka.publish(
            topic=config.KAFKA_TOPIC_RESULTS,
            message=result.model_dump(),
            key=job_id,
        )

        if success:
            logger.info(f"Published error result for job {job_id}")
        else:
            logger.error(f"Failed to publish error result for job {job_id}")

        return {
            "result_published": success,
        }

    except Exception as e:
        logger.error(f"Failed to publish error result: {e}")
        return {
            "result_published": False,
            "error": str(e),
        }
