"""
Retrieve Episodes Node for MainGraph
Node 5: retrieve_episodes

Fetches relevant episodic memories from both SQLite (short-term)
and mem0 (long-term), then merges and ranks results.
"""

from typing import Dict, Any, List
import logging
from app.shared.types import MainGraphState
from app.shared.normalize import normalize_mem0_items
from app.clients.long_term_client import get_long_term_client

logger = logging.getLogger(__name__)


def retrieve_episodes(state: MainGraphState) -> Dict[str, Any]:
    """
    Retrieve relevant episodic memories from both SQLite and mem0.

    1. Query SQLite for recent episodic memories
    2. Query mem0 for long-term memories
    3. Merge and rank results

    Args:
        state: Current graph state

    Returns:
        State updates with retrieved_episodes, retrieval_query, retrieval_error
    """
    user_id = state.get("user_id")

    if not user_id:
        return {
            "retrieved_episodes": [],
            "retrieval_query": "",
            "retrieval_error": "user_id is required"
        }

    # Build retrieval query
    retrieval_query = _build_retrieval_query(state)

    # Get limit from state or config
    retrieve_limit = state.get("retrieve_limit")
    if retrieve_limit is None:
        from app.config import config
        retrieve_limit = config.EPISODE_RETRIEVE_LIMIT

    all_episodes: List[Dict[str, Any]] = []
    errors: List[str] = []

    # 1. Query SQLite for episodic memories
    sqlite_episodes = _query_sqlite_episodes(
        user_id=user_id,
        state=state,
        limit=retrieve_limit
    )
    all_episodes.extend(sqlite_episodes)

    # 2. Query long-term memory (Supermemory or Mem0)
    try:
        client = get_long_term_client()
        response = client.search(
            user_id=user_id,
            query=retrieval_query,
            limit=retrieve_limit
        )

        if response.get("success", True):
            raw_data = response.get("data")
            lt_episodes = normalize_mem0_items(raw_data)
            # Mark source
            for ep in lt_episodes:
                ep["source"] = "long_term"
            all_episodes.extend(lt_episodes)
        else:
            errors.append(f"Long-term memory search: {response.get('message')}")

    except Exception as e:
        errors.append(f"Long-term memory error: {str(e)}")

    # 3. Fetch user profile if Supermemory is enabled
    try:
        profile = client.get_profile(user_id=user_id, query=retrieval_query)
        if profile:
            # Inject static profile facts as high-priority episodes
            for fact in profile.get("static", []):
                fact["source"] = "profile_static"
                fact["score"] = 0.9  # High priority
                all_episodes.append(fact)
    except Exception as e:
        errors.append(f"Profile fetch error: {str(e)}")

    # 4. Merge, deduplicate, and rank
    merged = _merge_and_rank(all_episodes, state, retrieve_limit)

    retrieval_error = "; ".join(errors) if errors else None

    # Emit search event for monitoring
    from app.monitor import get_monitor
    get_monitor().emit("search_executed", {
        "graph": "main_graph",
        "node": "retrieve_episodes",
        "result_count": len(merged),
        "sources": list({ep.get("source", "unknown") for ep in merged}),
    })

    return {
        "retrieved_episodes": merged,
        "retrieval_query": retrieval_query,
        "retrieval_error": retrieval_error
    }


def _query_sqlite_episodes(
    user_id: str,
    state: MainGraphState,
    limit: int
) -> List[Dict[str, Any]]:
    """
    Query SQLite for relevant episodic memories.
    """
    try:
        from app.storage import get_episode_repository, EpisodeQuery

        repo = get_episode_repository()

        # Build query
        query = EpisodeQuery(
            user_id=user_id,
            query_text=state.get("normalized_prompt", state.get("prompt", "")),
            task_types=[state.get("task_type")] if state.get("task_type") else None,
            apps=[state.get("app")] if state.get("app") else None,
            entities=state.get("entities"),
            recent_days=30,  # Focus on recent episodes
            limit=limit,
            boost_recent=True,
            boost_reinforced=True
        )

        # Search
        response = repo.search_episodes(query)

        # Convert to dict format
        episodes = []
        for result in response.episodes:
            ep_dict = result.episode.model_dump()
            ep_dict["score"] = result.score
            ep_dict["source"] = "sqlite"
            ep_dict["match_reasons"] = result.match_reasons
            episodes.append(ep_dict)

        logger.debug(f"Retrieved {len(episodes)} episodes from SQLite")
        return episodes

    except Exception as e:
        logger.warning(f"SQLite episode query failed: {str(e)}")
        return []


def _merge_and_rank(
    episodes: List[Dict[str, Any]],
    state: MainGraphState,
    limit: int
) -> List[Dict[str, Any]]:
    """
    Merge episodes from multiple sources and rank by relevance.
    """
    if not episodes:
        return []

    # Deduplicate by text (simple approach)
    seen_texts = set()
    unique = []
    for ep in episodes:
        text = ep.get("text", ep.get("memory", ""))[:100]
        if text and text not in seen_texts:
            seen_texts.add(text)
            unique.append(ep)

    # Sort by score (if available) then by recency
    def score_key(ep):
        score = ep.get("score", 0.5)
        # Boost sqlite (short-term, more recent/relevant)
        if ep.get("source") == "sqlite":
            score += 0.1
        return score

    unique.sort(key=score_key, reverse=True)

    return unique[:limit]


def _build_retrieval_query(state: MainGraphState) -> str:
    """
    Build deterministic retrieval query from state.

    Format: {task_type} {app} {entities} {normalized_prompt}

    Args:
        state: Current state

    Returns:
        Query string
    """
    parts = []

    task_type = state.get("task_type", "")
    if task_type and task_type not in ["unknown", "chat"]:
        parts.append(task_type)

    app = state.get("app", "")
    if app:
        parts.append(app)

    entities = state.get("entities", [])
    if entities:
        # Add first few entities
        parts.extend(entities[:3])

    normalized_prompt = state.get("normalized_prompt", state.get("prompt", ""))
    if normalized_prompt:
        parts.append(normalized_prompt)

    return " ".join(parts)
