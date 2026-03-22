"""
Compose Context Node for MainGraph
Node 6: compose_context

Builds the final context dict sent to the LLM.
"""

from typing import Dict, Any
from app.shared.types import MainGraphState


def compose_context(state: MainGraphState) -> Dict[str, Any]:
    """
    Compose LLM context from state.

    Combines:
    - Persona/style rules
    - Structured memory (mem0)
    - Retrieved episodes
    - Task context
    - User prompt

    Args:
        state: Current graph state

    Returns:
        State updates with llm_context
    """
    normalized_prompt = state.get("normalized_prompt", state.get("prompt", ""))
    task_type = state.get("task_type", "unknown")
    app = state.get("app")
    entities = state.get("entities", [])
    mem0_state = state.get("mem0_state", {})
    user_profile = state.get("user_profile")
    retrieved_episodes = state.get("retrieved_episodes", [])

    # Import config for limits
    from app.config import config

    # Build context dict
    llm_context = {
        "persona": {
            "name": "Jarvis",
            "style_rules": [
                "Be concise and actionable",
                "Ask for approval when needed",
                "Never invent credentials"
            ]
        },
        "structured_memory": _truncate_mem0_state(mem0_state, config.MAX_MEM0_ITEMS_IN_CONTEXT),
        "retrieved_episodes": _truncate_episodes(retrieved_episodes, config.MAX_EPISODES_IN_CONTEXT),
        "task": {
            "task_type": task_type,
            "app": app,
            "entities": entities
        },
        "user_prompt": normalized_prompt
    }

    # Inject Supermemory user profile if available
    if user_profile:
        llm_context["user_profile"] = {
            "static_facts": user_profile.get("static", [])[:10],
            "dynamic_context": user_profile.get("dynamic", [])[:5],
        }

    return {
        "llm_context": llm_context
    }


def _truncate_mem0_state(mem0_state: Dict[str, Any], max_items: int) -> Dict[str, Any]:
    """Truncate mem0 state to keep context size manageable"""
    if not mem0_state:
        return {"items": [], "summary": {"count": 0}}

    items = mem0_state.get("items", [])
    truncated_items = items[:max_items]

    return {
        "items": truncated_items,
        "summary": {
            "count": len(items),
            "shown": len(truncated_items),
            "truncated": len(items) > max_items
        }
    }


def _truncate_episodes(episodes: list, max_episodes: int) -> list:
    """Truncate episodes to keep context size manageable"""
    if not episodes:
        return []

    # Take top N episodes
    truncated = episodes[:max_episodes]

    # Simplify episode structure for LLM
    simplified = []
    for ep_result in truncated:
        if isinstance(ep_result, dict) and "episode" in ep_result:
            episode = ep_result["episode"]
            score = ep_result.get("score", 0.0)
        else:
            episode = ep_result
            score = 0.0

        simplified.append({
            "text": episode.get("text", ""),
            "task_type": episode.get("task_type"),
            "app": episode.get("app"),
            "importance": episode.get("importance_score", 0.0),
            "relevance": score
        })

    return simplified
