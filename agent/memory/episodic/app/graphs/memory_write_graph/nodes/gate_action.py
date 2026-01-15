"""
Gate Action Router Node

Routes episodes to: save, ignore, or save_and_promote.
"""

from typing import Literal
import logging

from ..state import MemoryWriteState

logger = logging.getLogger(__name__)


def gate_action(state: MemoryWriteState) -> Literal["save", "ignore", "save_and_promote"]:
    """
    Router to decide episode fate.

    Decision logic:
    1. No candidates -> ignore
    2. High importance (>0.8) and high confidence (>0.9) -> save_and_promote
    3. Otherwise -> save

    Args:
        state: Current graph state

    Returns:
        "save", "ignore", or "save_and_promote"
    """
    candidates = state.get("episode_candidates", [])

    # No candidates to process
    if not candidates:
        logger.debug("No candidates, routing to ignore")
        return "ignore"

    # Check for high-value candidates that should be fast-tracked
    for candidate in candidates:
        importance = candidate.get("importance_score", 0.5)
        confidence = candidate.get("confidence", 1.0)

        # High importance + high confidence = fast-track to promotion
        if importance >= 0.8 and confidence >= 0.9:
            logger.info(f"High-value candidate detected (importance={importance}), routing to save_and_promote")
            return "save_and_promote"

    # Default: normal save flow
    logger.debug("Routing to save")
    return "save"
