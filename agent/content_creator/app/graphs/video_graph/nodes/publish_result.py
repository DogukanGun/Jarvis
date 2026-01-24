"""
Publish Result Node.

Publishes the success result to Kafka.
"""
import logging
from typing import Dict, Any

from app.clients.kafka_client import get_kafka_client
from app.schemas.messages import RenderResult
from app.config import config
from app.graphs.video_graph.state import VideoGraphState

logger = logging.getLogger(__name__)


def publish_result_node(state: VideoGraphState) -> Dict[str, Any]:
    """
    Publish the video generation result to Kafka.

    Args:
        state: Current graph state

    Returns:
        State update with result_published
    """
    job_id = state.get("job_id", "unknown")
    response_url = state.get("response_url")

    if not response_url:
        logger.error(f"No response URL for job {job_id}")
        return {
            "result_published": False,
            "error": "No response URL to publish",
        }

    logger.info(f"Publishing success result for job {job_id}...")

    try:
        result = RenderResult.success_result(
            job_id=job_id,
            url=response_url,
        )

        kafka = get_kafka_client()
        success = kafka.publish(
            topic=config.KAFKA_TOPIC_RESULTS,
            message=result.model_dump(),
            key=job_id,
        )

        if success:
            logger.info(f"Published success result for job {job_id}")
        else:
            logger.error(f"Failed to publish result for job {job_id}")

        return {
            "result_published": success,
        }

    except Exception as e:
        logger.error(f"Publish error for job {job_id}: {e}")
        return {
            "result_published": False,
            "error": str(e),
        }
