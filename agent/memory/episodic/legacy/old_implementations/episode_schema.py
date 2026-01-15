"""
Episode Schema for Jarvis Episodic Memory

Defines the structure of episodic memories and their metadata.
"""

from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class EpisodeType(Enum):
    """Types of episodic memories"""
    INTERACTION = "interaction"          # User-agent interaction
    TASK_COMPLETION = "task_completion"  # Completed task
    ERROR = "error"                      # Error/failure event
    OBSERVATION = "observation"          # System observation
    USER_FEEDBACK = "user_feedback"      # Explicit user feedback


class Episode(TypedDict, total=False):
    """
    Episode structure for episodic memory.

    Each episode captures a specific interaction or event with rich context.
    """
    # Core identification
    id: str                              # Unique episode ID
    user_id: str                         # User identifier

    # Content
    text: str                            # Main episode text/description
    summary: Optional[str]               # Brief summary (optional)

    # Metadata
    episode_type: str                    # Type from EpisodeType enum
    task_type: Optional[str]             # Task type from preprocess (if applicable)
    app: Optional[str]                   # App context (gmail, linkedin, etc.)
    entities: List[str]                  # Extracted entities

    # Temporal
    timestamp: str                       # ISO format timestamp
    created_at: str                      # Episode creation time

    # Embeddings for semantic search
    embedding: Optional[List[float]]     # Vector embedding of text

    # Context
    prompt: Optional[str]                # Original user prompt
    response: Optional[str]              # Agent response
    context_snapshot: Optional[Dict[str, Any]]  # Context at time of episode

    # Quality and importance
    importance_score: float              # 0.0 to 1.0, higher = more important
    reinforcement_count: int             # Times this episode was reinforced
    confidence: float                    # Confidence in episode accuracy (0.0-1.0)

    # Relations
    related_episode_ids: List[str]       # IDs of related episodes
    tags: List[str]                      # User or system tags

    # Status
    is_deleted: bool                     # Soft delete flag
    verified: bool                       # User verified this episode


class EpisodeQuery(TypedDict, total=False):
    """Query parameters for episode retrieval"""
    # Required
    user_id: str                         # User to query for

    # Semantic search
    query_text: Optional[str]            # Text to search semantically
    query_embedding: Optional[List[float]]  # Pre-computed embedding

    # Filters
    task_types: Optional[List[str]]      # Filter by task types
    apps: Optional[List[str]]            # Filter by apps
    episode_types: Optional[List[str]]   # Filter by episode types
    entities: Optional[List[str]]        # Must contain these entities
    tags: Optional[List[str]]            # Must have these tags

    # Temporal filters
    after_timestamp: Optional[str]       # Episodes after this time (ISO)
    before_timestamp: Optional[str]      # Episodes before this time (ISO)
    recent_days: Optional[int]           # Episodes from last N days

    # Quality filters
    min_importance: Optional[float]      # Minimum importance score
    min_confidence: Optional[float]      # Minimum confidence
    verified_only: Optional[bool]        # Only verified episodes

    # Pagination
    limit: int                           # Max number of results (default 10)
    offset: int                          # Offset for pagination (default 0)

    # Ranking
    boost_recent: bool                   # Boost recent episodes (default True)
    boost_reinforced: bool               # Boost frequently reinforced (default True)


class EpisodeSearchResult(TypedDict):
    """Single search result with score"""
    episode: Episode                     # The episode
    score: float                         # Relevance score (0.0-1.0)
    match_reasons: List[str]             # Why this episode matched


class EpisodeRetrievalResult(TypedDict):
    """Result of episode retrieval"""
    episodes: List[EpisodeSearchResult]  # Ranked results
    total_count: int                     # Total matching episodes (before limit)
    query_time_ms: float                 # Query execution time
    used_filters: Dict[str, Any]         # Filters that were applied
    metadata: Dict[str, Any]             # Additional metadata


# Default values
DEFAULT_LIMIT = 10
DEFAULT_OFFSET = 0
DEFAULT_MIN_IMPORTANCE = 0.0
DEFAULT_MIN_CONFIDENCE = 0.0
DEFAULT_BOOST_RECENT = True
DEFAULT_BOOST_REINFORCED = True


def create_episode(
    user_id: str,
    text: str,
    episode_type: EpisodeType,
    task_type: Optional[str] = None,
    app: Optional[str] = None,
    entities: Optional[List[str]] = None,
    importance_score: float = 0.5,
    **kwargs
) -> Episode:
    """
    Helper function to create a well-formed episode.

    Args:
        user_id: User identifier
        text: Main episode text
        episode_type: Type of episode
        task_type: Optional task type
        app: Optional app context
        entities: Optional entity list
        importance_score: Importance (0.0-1.0)
        **kwargs: Additional episode fields

    Returns:
        Episode dict with all required fields
    """
    import uuid
    from datetime import datetime

    episode: Episode = {
        "id": kwargs.get("id", str(uuid.uuid4())),
        "user_id": user_id,
        "text": text,
        "episode_type": episode_type.value,
        "task_type": task_type,
        "app": app,
        "entities": entities or [],
        "timestamp": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
        "importance_score": max(0.0, min(1.0, importance_score)),
        "reinforcement_count": 0,
        "confidence": 1.0,
        "related_episode_ids": [],
        "tags": [],
        "is_deleted": False,
        "verified": False,
    }

    # Add any additional fields from kwargs
    for key, value in kwargs.items():
        if key not in episode and key in Episode.__annotations__:
            episode[key] = value

    return episode


def validate_episode(episode: Episode) -> tuple[bool, Optional[str]]:
    """
    Validate an episode structure.

    Args:
        episode: Episode to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Required fields
    required_fields = ["id", "user_id", "text", "episode_type", "timestamp"]

    for field in required_fields:
        if field not in episode or episode[field] is None:
            return False, f"Missing required field: {field}"

    # Validate episode_type
    valid_types = [t.value for t in EpisodeType]
    if episode["episode_type"] not in valid_types:
        return False, f"Invalid episode_type: {episode['episode_type']}"

    # Validate importance_score range
    if "importance_score" in episode:
        score = episode["importance_score"]
        if not (0.0 <= score <= 1.0):
            return False, f"importance_score must be 0.0-1.0, got {score}"

    # Validate confidence range
    if "confidence" in episode:
        conf = episode["confidence"]
        if not (0.0 <= conf <= 1.0):
            return False, f"confidence must be 0.0-1.0, got {conf}"

    return True, None
