"""
Retrieve Episodes Node for Jarvis MainGraph
Node 5: retrieve_episodes

Retrieves relevant episodic memories based on current context.
"""

from typing import TypedDict, Optional, List, Dict, Any
from episode_schema import EpisodeQuery, EpisodeSearchResult, DEFAULT_LIMIT
from episode_storage import get_episode_storage
from datetime import datetime, timedelta


class GraphState(TypedDict, total=False):
    """Extended graph state for episode retrieval"""
    # From previous nodes
    prompt: str
    normalized_prompt: str
    task_type: str
    app: Optional[str]
    entities: List[str]
    context: Optional[Dict[str, Any]]
    mem0_items: List[Dict[str, Any]]

    # Episode retrieval inputs
    user_id: str
    query_embedding: Optional[List[float]]  # Pre-computed if available

    # Episode retrieval outputs
    retrieved_episodes: List[EpisodeSearchResult]
    episode_retrieval_error: Optional[str]
    episode_retrieval_meta: Dict[str, Any]


def build_episode_query(state: GraphState) -> EpisodeQuery:
    """
    Build episode query from current state.

    Extracts relevant information from preprocessing and mem0 to create
    a targeted episode search query.

    Args:
        state: Current graph state

    Returns:
        EpisodeQuery for searching episodes
    """
    user_id = state.get("user_id", "")
    normalized_prompt = state.get("normalized_prompt", "")
    task_type = state.get("task_type")
    app = state.get("app")
    entities = state.get("entities", [])
    context = state.get("context") or {}
    query_embedding = state.get("query_embedding")

    # Base query
    query: EpisodeQuery = {
        "user_id": user_id,
        "query_text": normalized_prompt,
        "query_embedding": query_embedding,
        "limit": DEFAULT_LIMIT,
        "offset": 0,
        "boost_recent": True,
        "boost_reinforced": True,
    }

    # Add task type filter if present
    if task_type and task_type != "unknown" and task_type != "chat":
        query["task_types"] = [task_type]

    # Add app filter if present
    if app:
        query["apps"] = [app]

    # Add entity filter if we have entities
    if entities:
        query["entities"] = entities

    # Temporal filter: prioritize recent episodes
    recent_days = context.get("episode_recent_days", 30)
    if recent_days:
        query["recent_days"] = recent_days

    # Quality filters
    min_importance = context.get("episode_min_importance", 0.3)
    query["min_importance"] = min_importance

    min_confidence = context.get("episode_min_confidence", 0.5)
    query["min_confidence"] = min_confidence

    # Limit from context
    episode_limit = context.get("episode_limit")
    if episode_limit:
        query["limit"] = episode_limit

    return query


def retrieve_episodes(state: GraphState, storage=None) -> Dict[str, Any]:
    """
    Retrieve relevant episodic memories.

    Main node function that:
    1. Builds query from current state
    2. Searches episode storage
    3. Returns ranked results

    Args:
        state: Current graph state (must contain user_id)
        storage: Optional storage for testing (defaults to get_episode_storage())

    Returns:
        State updates with retrieved_episodes, error, and metadata
    """
    user_id = state.get("user_id")

    if not user_id:
        return {
            "retrieved_episodes": [],
            "episode_retrieval_error": "user_id is required for episode retrieval",
            "episode_retrieval_meta": {
                "query_built": False,
                "episodes_found": 0
            }
        }

    try:
        # Build query from state
        query = build_episode_query(state)

        # Get storage (use injected storage for testing)
        if storage is None:
            storage = get_episode_storage()

        # Execute search
        result = storage.search(query)

        # Extract episodes
        episodes = result.get("episodes", [])
        total_count = result.get("total_count", 0)
        query_time_ms = result.get("query_time_ms", 0.0)
        used_filters = result.get("used_filters", {})

        # Build metadata
        meta = {
            "query_built": True,
            "episodes_found": total_count,
            "episodes_returned": len(episodes),
            "query_time_ms": query_time_ms,
            "used_filters": used_filters,
            "query_text": query.get("query_text", ""),
            "had_embedding": query.get("query_embedding") is not None,
        }

        return {
            "retrieved_episodes": episodes,
            "episode_retrieval_error": None,
            "episode_retrieval_meta": meta,
        }

    except Exception as e:
        # Handle any unexpected errors
        return {
            "retrieved_episodes": [],
            "episode_retrieval_error": f"Error retrieving episodes: {str(e)}",
            "episode_retrieval_meta": {
                "query_built": False,
                "episodes_found": 0,
                "error": str(e)
            }
        }


def filter_episodes_by_relevance(
    episodes: List[EpisodeSearchResult],
    min_score: float = 0.3
) -> List[EpisodeSearchResult]:
    """
    Filter episodes by minimum relevance score.

    Can be used as a post-processing step after retrieval.

    Args:
        episodes: Retrieved episodes with scores
        min_score: Minimum score threshold (0.0-1.0)

    Returns:
        Filtered episodes list
    """
    return [ep for ep in episodes if ep.get("score", 0.0) >= min_score]


def get_top_episodes(
    episodes: List[EpisodeSearchResult],
    n: int = 5
) -> List[EpisodeSearchResult]:
    """
    Get top N episodes by score.

    Args:
        episodes: Retrieved episodes
        n: Number of top episodes to return

    Returns:
        Top N episodes
    """
    return episodes[:n]


def extract_episode_context(episodes: List[EpisodeSearchResult]) -> Dict[str, Any]:
    """
    Extract useful context from retrieved episodes.

    Aggregates information across episodes for downstream use.

    Args:
        episodes: Retrieved episodes

    Returns:
        Aggregated context dict
    """
    if not episodes:
        return {
            "has_episodes": False,
            "episode_count": 0
        }

    # Extract common patterns
    task_types = []
    apps = []
    all_entities = []
    importance_scores = []
    timestamps = []

    for result in episodes:
        episode = result.get("episode", {})

        if episode.get("task_type"):
            task_types.append(episode["task_type"])

        if episode.get("app"):
            apps.append(episode["app"])

        all_entities.extend(episode.get("entities", []))

        importance_scores.append(episode.get("importance_score", 0.0))

        if episode.get("timestamp"):
            timestamps.append(episode["timestamp"])

    # Most common task type
    most_common_task = max(set(task_types), key=task_types.count) if task_types else None

    # Most common app
    most_common_app = max(set(apps), key=apps.count) if apps else None

    # Most frequent entities
    entity_counts = {}
    for entity in all_entities:
        entity_counts[entity] = entity_counts.get(entity, 0) + 1

    top_entities = sorted(
        entity_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    # Average importance
    avg_importance = sum(importance_scores) / len(importance_scores) if importance_scores else 0.0

    # Recency
    if timestamps:
        latest = max(timestamps)
        oldest = min(timestamps)
    else:
        latest = oldest = None

    return {
        "has_episodes": True,
        "episode_count": len(episodes),
        "most_common_task_type": most_common_task,
        "most_common_app": most_common_app,
        "top_entities": [entity for entity, _ in top_entities],
        "avg_importance": avg_importance,
        "latest_timestamp": latest,
        "oldest_timestamp": oldest,
        "avg_score": sum(ep.get("score", 0.0) for ep in episodes) / len(episodes),
    }
