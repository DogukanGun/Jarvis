"""
Extract Patterns Node

Finds recurring patterns in recent episodes by fingerprint grouping.
"""

from typing import Dict, Any, List
from collections import defaultdict
from datetime import datetime
import logging

from ..state import ReflectionState

logger = logging.getLogger(__name__)


def extract_patterns(state: ReflectionState) -> Dict[str, Any]:
    """
    Extract recurring patterns from episodes.

    Groups episodes by fingerprint and identifies patterns
    based on frequency and recency.

    Args:
        state: Current graph state

    Returns:
        State updates with detected_patterns
    """
    from app.config import config

    episodes = state.get("recent_episodes", [])
    min_count = config.REFLECTION_MIN_PATTERN_COUNT

    if not episodes:
        logger.debug("No episodes to analyze")
        return {
            "detected_patterns": [],
            "pattern_count": 0
        }

    try:
        # Group by fingerprint
        fingerprint_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for episode in episodes:
            fp = episode.get("fingerprint")
            if fp:
                fingerprint_groups[fp].append(episode)

        # Find patterns (fingerprints with multiple occurrences)
        patterns: List[Dict[str, Any]] = []

        for fingerprint, group in fingerprint_groups.items():
            if len(group) >= min_count:
                pattern = _build_pattern(fingerprint, group)
                patterns.append(pattern)

        # Sort by confidence (frequency * recency)
        patterns.sort(key=lambda p: p["confidence"], reverse=True)

        logger.info(f"Extracted {len(patterns)} patterns from {len(episodes)} episodes")

        return {
            "detected_patterns": patterns,
            "pattern_count": len(patterns)
        }

    except Exception as e:
        error_msg = f"Pattern extraction error: {str(e)}"
        logger.error(error_msg)
        return {
            "detected_patterns": [],
            "pattern_count": 0,
            "errors": state.get("errors", []) + [error_msg]
        }


def _build_pattern(fingerprint: str, episodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a pattern from a group of episodes with the same fingerprint.
    """
    # Get the most recent episode as representative
    sorted_episodes = sorted(
        episodes,
        key=lambda e: e.get("last_seen", ""),
        reverse=True
    )
    representative = sorted_episodes[0]

    # Calculate total reinforcement
    total_count = sum(e.get("reinforcement_count", 1) for e in episodes)

    # Calculate average importance
    avg_importance = sum(e.get("importance_score", 0.5) for e in episodes) / len(episodes)

    # Calculate recency score (0-1, higher = more recent)
    try:
        most_recent = datetime.fromisoformat(representative.get("last_seen", ""))
        days_old = (datetime.utcnow() - most_recent).days
        recency_score = max(0, 1 - (days_old / 30))
    except Exception:
        recency_score = 0.5

    # Calculate confidence
    frequency_score = min(total_count / 10, 1.0)
    confidence = (frequency_score * 0.5) + (recency_score * 0.3) + (avg_importance * 0.2)

    return {
        "fingerprint": fingerprint,
        "episode_ids": [e.get("id") for e in episodes],
        "count": len(episodes),
        "total_reinforcement": total_count,
        "representative_text": representative.get("text", ""),
        "representative_summary": representative.get("summary"),
        "task_type": representative.get("task_type"),
        "app": representative.get("app"),
        "entities": representative.get("entities", []),
        "avg_importance": avg_importance,
        "recency_score": recency_score,
        "confidence": confidence
    }
