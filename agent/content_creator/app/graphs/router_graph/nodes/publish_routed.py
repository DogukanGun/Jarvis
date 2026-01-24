"""
Publish Routed Node.

Publishes validated request to the target worker topic.
"""
import logging
from typing import Dict, Any

from app.clients.kafka_client import get_kafka_client
from app.graphs.router_graph.state import RouterGraphState

logger = logging.getLogger(__name__)


def publish_routed_node(state: RouterGraphState) -> Dict[str, Any]:
    """
    Publish the validated request to the target worker topic.

    Args:
        state: Current graph state with request and target_topic

    Returns:
        State update with publish_success
    """
    target_topic = state.get("target_topic")
    request = state.get("request", {})
    job_id = state.get("job_id", "unknown")

    if not target_topic:
        logger.error(f"No target topic for job {job_id}")
        return {
            "publish_success": False,
            "error": "No target topic",
        }

    try:
        kafka = get_kafka_client()
        success = kafka.publish(
            topic=target_topic,
            message=request,
            key=job_id,
        )

        if success:
            logger.info(f"Published job {job_id} to {target_topic}")
        else:
            logger.error(f"Failed to publish job {job_id} to {target_topic}")

        return {
            "publish_success": success,
        }

    except Exception as e:
        logger.error(f"Publish error for job {job_id}: {e}")
        return {
            "publish_success": False,
            "error": str(e),
        }
