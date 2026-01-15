"""
Promote Check Node

Router to decide if episode should be promoted to mem0.
"""

from typing import Literal
import logging

from ..state import MemoryWriteState

logger = logging.getLogger(__name__)


def promote_check(state: MemoryWriteState) -> Literal["yes", "no"]:
    """
    Check if episode meets promotion criteria.

    Promotion criteria:
    1. Reinforcement count >= threshold (default 3)
    2. Confidence >= threshold (default 0.7)
    3. Not already promoted
    4. OR gate_decision was "save_and_promote"

    Args:
        state: Current graph state

    Returns:
        "yes" or "no"
    """
    from app.config import config

    episode = state.get("episode", {})
    gate_decision = state.get("gate_decision")
    new_count = state.get("new_reinforcement_count", 1)

    # Fast-track promotion if gate said so
    if gate_decision == "save_and_promote":
        logger.info("Fast-track promotion (gate_decision=save_and_promote)")
        return "yes"

    # Already promoted?
    if episode.get("promoted_to_mem0"):
        logger.debug("Episode already promoted")
        return "no"

    # Check reinforcement count
    if new_count < config.PROMOTION_THRESHOLD_COUNT:
        logger.debug(f"Count {new_count} < threshold {config.PROMOTION_THRESHOLD_COUNT}")
        return "no"

    # Check confidence
    confidence = episode.get("confidence", 1.0)
    if confidence < config.PROMOTION_MIN_CONFIDENCE:
        logger.debug(f"Confidence {confidence} < threshold {config.PROMOTION_MIN_CONFIDENCE}")
        return "no"

    logger.info(f"Episode meets promotion criteria (count={new_count}, confidence={confidence})")
    return "yes"
