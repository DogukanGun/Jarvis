"""
Handle Error Node.

Publishes error result when editing fails.
"""
import logging
from typing import Dict, Any

from app.clients.kafka_client import get_kafka_client
from app.schemas.messages import RenderResult
from app.config import config
from app.graphs.image_edit_graph.state import ImageEditGraphState

logger = logging.getLogger(__name__)


def handle_error_node(state: ImageEditGraphState) -> Dict[str, Any]:
    """
    Handle edit error by publishing error result.

    Args:
        state: Current graph state with error information

    Returns:
        State update with result_published
    """
    job_id = state.get("job_id", "unknown")

    error_msg = (
        state.get("error")
        or state.get("source_error")
        or state.get("model_error")
        or state.get("edit_error")
        or state.get("upload_error")
        or "Unknown error"
    )

    logger.warning(f"Publishing error result for job {job_id}: {error_msg}")

    try:
        result = RenderResult.error_result(
            job_id=job_id,
            error=error_msg,
        )

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
        }
