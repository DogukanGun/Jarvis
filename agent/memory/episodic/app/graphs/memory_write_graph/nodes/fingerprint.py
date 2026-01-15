"""
Fingerprint Node

Generates deterministic hash for episode deduplication.
"""

from typing import Dict, Any
import logging

from ..state import MemoryWriteState
from app.storage.fingerprint import generate_fingerprint

logger = logging.getLogger(__name__)


def fingerprint_node(state: MemoryWriteState) -> Dict[str, Any]:
    """
    Generate fingerprint for the first candidate.

    Fingerprint = SHA256(episode_type + task_type + app + entities + summary)

    Args:
        state: Current graph state

    Returns:
        State updates with fingerprint, fingerprint_input
    """
    candidates = state.get("redacted_candidates", state.get("episode_candidates", []))

    if not candidates:
        logger.warning("No candidates to fingerprint")
        return {
            "fingerprint": "",
            "fingerprint_input": ""
        }

    # Use first candidate for fingerprinting
    candidate = candidates[0]

    # Generate fingerprint
    fp = generate_fingerprint(
        episode_type=candidate.get("episode_type", "interaction"),
        task_type=candidate.get("task_type"),
        app=candidate.get("app"),
        entities=candidate.get("entities", []),
        summary=candidate.get("summary"),
        text=candidate.get("text")
    )

    # Build fingerprint input for debugging
    fp_input = f"{candidate.get('episode_type')}::{candidate.get('task_type')}::{candidate.get('app')}"

    logger.debug(f"Generated fingerprint: {fp[:16]}...")

    return {
        "fingerprint": fp,
        "fingerprint_input": fp_input
    }
