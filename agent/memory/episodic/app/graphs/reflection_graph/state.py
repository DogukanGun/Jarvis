"""
Reflection Graph State Definition

State schema for periodic pattern extraction.
"""

from typing import TypedDict, Optional, List, Dict, Any


class ReflectionState(TypedDict, total=False):
    """
    State for reflection_graph.

    Tracks pattern extraction from recent episodes.
    """

    # =========================================================================
    # Input
    # =========================================================================
    user_id: str
    lookback_days: int

    # =========================================================================
    # load_recent_episodes
    # =========================================================================
    recent_episodes: List[Dict[str, Any]]
    episode_count: int

    # =========================================================================
    # extract_patterns
    # =========================================================================
    detected_patterns: List[Dict[str, Any]]
    pattern_count: int

    # =========================================================================
    # resolve_conflicts
    # =========================================================================
    resolved_patterns: List[Dict[str, Any]]
    conflicts_resolved: int

    # =========================================================================
    # create_promotion_proposals
    # =========================================================================
    proposals_created: List[str]  # Proposal IDs
    proposals_count: int

    # =========================================================================
    # Status
    # =========================================================================
    completed: bool
    errors: List[str]
