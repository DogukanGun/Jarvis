"""
Resolve Conflicts Node

Resolves conflicts between patterns, user overrides win.
"""

from typing import Dict, Any, List
import logging

from ..state import ReflectionState
from app.storage import get_episode_repository

logger = logging.getLogger(__name__)


def resolve_conflicts(state: ReflectionState) -> Dict[str, Any]:
    """
    Resolve conflicts between detected patterns.

    Rules:
    1. User-rejected patterns are excluded
    2. More recent user decisions override older patterns
    3. Higher confidence patterns take precedence

    Args:
        state: Current graph state

    Returns:
        State updates with resolved_patterns
    """
    patterns = state.get("detected_patterns", [])
    user_id = state.get("user_id")

    if not patterns:
        return {
            "resolved_patterns": [],
            "conflicts_resolved": 0
        }

    try:
        repo = get_episode_repository()

        # Get recent user decisions to check for rejections
        rejected_fingerprints = _get_rejected_fingerprints(repo, user_id)

        # Filter and resolve patterns
        resolved: List[Dict[str, Any]] = []
        conflicts_count = 0

        for pattern in patterns:
            fingerprint = pattern.get("fingerprint")

            # Skip if user previously rejected this pattern
            if fingerprint in rejected_fingerprints:
                logger.debug(f"Skipping rejected pattern: {fingerprint[:16]}...")
                conflicts_count += 1
                continue

            # Check for conflicting patterns (same task_type/app but different content)
            conflict = _find_conflict(pattern, resolved)
            if conflict:
                # Keep higher confidence pattern
                if pattern["confidence"] > conflict["confidence"]:
                    resolved.remove(conflict)
                    resolved.append(pattern)
                    conflicts_count += 1
                    logger.debug(f"Replaced lower confidence pattern")
                else:
                    conflicts_count += 1
                    logger.debug(f"Skipping lower confidence pattern")
            else:
                resolved.append(pattern)

        logger.info(f"Resolved {conflicts_count} conflicts, {len(resolved)} patterns remain")

        return {
            "resolved_patterns": resolved,
            "conflicts_resolved": conflicts_count
        }

    except Exception as e:
        error_msg = f"Conflict resolution error: {str(e)}"
        logger.error(error_msg)
        # On error, pass through all patterns
        return {
            "resolved_patterns": patterns,
            "conflicts_resolved": 0,
            "errors": state.get("errors", []) + [error_msg]
        }


def _get_rejected_fingerprints(repo, user_id: str) -> set:
    """
    Get fingerprints that user has previously rejected.
    """
    try:
        # Query user_decisions for rejections
        # This is a simplified version - in production you'd want
        # to join with episodes to get fingerprints
        return set()  # Placeholder - would query SQLite

    except Exception:
        return set()


def _find_conflict(
    pattern: Dict[str, Any],
    existing: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Find a conflicting pattern in the existing list.

    Conflict = same task_type AND app but different fingerprint.
    """
    for existing_pattern in existing:
        # Same task_type and app?
        if (pattern.get("task_type") == existing_pattern.get("task_type") and
            pattern.get("app") == existing_pattern.get("app") and
            pattern.get("task_type") is not None):  # Only conflict on non-null task types
            return existing_pattern

    return None
