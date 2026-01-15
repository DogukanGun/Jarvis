"""
Build Episode Candidates Node

Extracts meaningful episode candidates from memory_intents and interaction data.
"""

from typing import Dict, Any, List
import logging

from ..state import MemoryWriteState

logger = logging.getLogger(__name__)


def build_episode_candidates(state: MemoryWriteState) -> Dict[str, Any]:
    """
    Build episode candidates from memory_intents and interaction data.

    Filters to keep only meaningful candidates worth storing.

    Args:
        state: Current graph state

    Returns:
        State updates with episode_candidates
    """
    candidates: List[Dict[str, Any]] = []
    errors: List[str] = []

    try:
        user_id = state.get("user_id")
        prompt = state.get("prompt", "")
        llm_output = state.get("llm_output", "")
        memory_intents = state.get("memory_intents") or {}

        # Skip if no user_id
        if not user_id:
            errors.append("user_id is required")
            return {
                "episode_candidates": [],
                "candidates_count": 0,
                "errors": errors
            }

        # Extract candidates from memory_intents
        intent_candidates = memory_intents.get("candidates", [])
        for candidate in intent_candidates:
            if _is_meaningful_candidate(candidate):
                candidates.append(_normalize_candidate(candidate, state))

        # If no explicit candidates, create one from the interaction
        if not candidates and prompt and llm_output:
            interaction_candidate = _build_interaction_candidate(state)
            if _is_meaningful_candidate(interaction_candidate):
                candidates.append(interaction_candidate)

        logger.info(f"Built {len(candidates)} episode candidates for user {user_id}")

        return {
            "episode_candidates": candidates,
            "candidates_count": len(candidates),
            "errors": errors
        }

    except Exception as e:
        error_msg = f"Error building candidates: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)

        return {
            "episode_candidates": [],
            "candidates_count": 0,
            "errors": errors
        }


def _is_meaningful_candidate(candidate: Dict[str, Any]) -> bool:
    """
    Check if a candidate is meaningful enough to store.

    Filters out:
    - Empty or very short text
    - Generic/trivial interactions
    - Low importance candidates
    """
    if not candidate:
        return False

    text = candidate.get("text", "")
    if not text or len(text.strip()) < 10:
        return False

    # Filter trivial patterns
    trivial_patterns = [
        "hello", "hi", "hey", "ok", "okay", "thanks", "thank you",
        "yes", "no", "sure", "got it", "understood"
    ]
    text_lower = text.lower().strip()
    if text_lower in trivial_patterns:
        return False

    # Check importance threshold
    importance = candidate.get("importance_score", 0.5)
    if importance < 0.2:
        return False

    return True


def _normalize_candidate(
    candidate: Dict[str, Any],
    state: MemoryWriteState
) -> Dict[str, Any]:
    """Normalize candidate structure with state defaults"""
    return {
        "text": candidate.get("text", ""),
        "summary": candidate.get("summary"),
        "episode_type": candidate.get("episode_type", "interaction"),
        "task_type": candidate.get("task_type") or state.get("task_type"),
        "app": candidate.get("app") or state.get("app"),
        "entities": candidate.get("entities") or state.get("entities", []),
        "importance_score": candidate.get("importance_score", 0.5),
        "confidence": candidate.get("confidence", 1.0),
    }


def _build_interaction_candidate(state: MemoryWriteState) -> Dict[str, Any]:
    """
    Build a candidate from the user-assistant interaction.

    Creates a summary of the interaction for storage.
    """
    prompt = state.get("prompt", "")
    llm_output = state.get("llm_output", "")
    task_type = state.get("task_type")
    app = state.get("app")

    # Build text from interaction
    if isinstance(llm_output, dict):
        response = llm_output.get("response", llm_output.get("answer", str(llm_output)))
    else:
        response = str(llm_output)

    # Create concise text
    text = f"User: {prompt[:200]}"
    if response:
        text += f"\nAssistant: {response[:200]}"

    # Build summary
    summary_parts = []
    if task_type and task_type not in ["unknown", "chat"]:
        summary_parts.append(f"Task: {task_type}")
    if app:
        summary_parts.append(f"App: {app}")
    summary = " | ".join(summary_parts) if summary_parts else None

    return {
        "text": text,
        "summary": summary,
        "episode_type": "interaction",
        "task_type": task_type,
        "app": app,
        "entities": state.get("entities", []),
        "importance_score": _estimate_importance(state),
        "confidence": 1.0,
    }


def _estimate_importance(state: MemoryWriteState) -> float:
    """
    Estimate importance score for an interaction.

    Higher importance for:
    - Specific tasks (not chat)
    - Interactions with detected apps
    - Interactions with entities
    """
    score = 0.5  # Base score

    task_type = state.get("task_type")
    if task_type and task_type not in ["unknown", "chat"]:
        score += 0.2

    if state.get("app"):
        score += 0.1

    entities = state.get("entities", [])
    if entities:
        score += min(len(entities) * 0.05, 0.2)

    return min(score, 1.0)
