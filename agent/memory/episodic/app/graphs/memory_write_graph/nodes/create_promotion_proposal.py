"""
Create Promotion Proposal Node

Creates a proposal to promote episode to mem0, queued for user approval.
"""

from typing import Dict, Any
from datetime import datetime, timedelta
import logging

from ..state import MemoryWriteState
from app.storage import get_episode_repository, PromotionProposal

logger = logging.getLogger(__name__)


def create_promotion_proposal(state: MemoryWriteState) -> Dict[str, Any]:
    """
    Create a promotion proposal for user approval.

    The proposal will be sent to Kafka for the main agent to
    present to the user. Expires after configured timeout.

    Args:
        state: Current graph state

    Returns:
        State updates with proposal_id, proposal, should_promote
    """
    from app.config import config

    episode_id = state.get("episode_id")
    episode = state.get("episode", {})
    user_id = state.get("user_id")

    if not episode_id or not user_id:
        logger.error("Missing episode_id or user_id for proposal")
        return {
            "proposal_id": None,
            "proposal": None,
            "should_promote": True,
            "promotion_reason": "Missing data for proposal creation"
        }

    try:
        # Build proposed value from episode
        proposed_value = _build_proposed_value(episode)

        # Find evidence (similar episodes)
        evidence = _find_evidence(user_id, episode.get("fingerprint"))

        # Create proposal
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=config.KAFKA_APPROVAL_TIMEOUT_SECONDS)

        proposal = PromotionProposal(
            episode_id=episode_id,
            user_id=user_id,
            target_path=_suggest_target_path(episode),
            proposed_value=proposed_value,
            confidence=episode.get("confidence", 1.0),
            evidence=evidence,
            status="pending",
            created_at=now,
            expires_at=expires_at
        )

        # Store proposal
        repo = get_episode_repository()
        proposal_id = repo.insert_proposal(proposal)

        # Update episode with proposal reference
        repo.update_episode(episode_id, {
            "promotion_proposal_id": proposal_id
        })

        logger.info(f"Created promotion proposal: {proposal_id} for episode {episode_id}")

        return {
            "proposal_id": proposal_id,
            "proposal": proposal.model_dump(),
            "should_promote": True,
            "promotion_reason": f"Reached threshold (count={state.get('new_reinforcement_count')})"
        }

    except Exception as e:
        error_msg = f"Proposal creation error: {str(e)}"
        logger.error(error_msg)
        return {
            "proposal_id": None,
            "proposal": None,
            "should_promote": True,
            "promotion_reason": error_msg
        }


def _build_proposed_value(episode: Dict[str, Any]) -> str:
    """
    Build a human-readable proposed value for mem0.

    Extracts the key insight from the episode.
    """
    summary = episode.get("summary")
    if summary:
        return summary

    text = episode.get("text", "")

    # Try to extract a concise statement
    # If text has "User: ... Assistant: ..." format, extract the pattern
    if "User:" in text and "Assistant:" in text:
        # Extract what the user typically does
        task_type = episode.get("task_type")
        app = episode.get("app")

        if task_type and app:
            return f"User frequently performs {task_type} tasks using {app}"
        elif task_type:
            return f"User frequently performs {task_type} tasks"
        elif app:
            return f"User frequently uses {app}"

    # Truncate text if too long
    if len(text) > 200:
        return text[:197] + "..."

    return text


def _suggest_target_path(episode: Dict[str, Any]) -> str:
    """
    Suggest a target path in mem0 for the promoted memory.

    Based on episode type, task type, and app.
    """
    episode_type = episode.get("episode_type", "interaction")
    task_type = episode.get("task_type")
    app = episode.get("app")

    if task_type:
        return f"preferences.{task_type}"
    elif app:
        return f"apps.{app}"
    else:
        return f"behaviors.{episode_type}"


def _find_evidence(user_id: str, fingerprint: str) -> list:
    """
    Find similar episodes as evidence for the proposal.

    Returns list of episode IDs that support this memory.
    """
    try:
        repo = get_episode_repository()
        # Get recent episodes with similar fingerprint
        recent = repo.get_recent_episodes(user_id, days=30, limit=10)

        evidence = []
        for ep in recent:
            if ep.fingerprint == fingerprint:
                evidence.append(ep.id)

        return evidence[:5]  # Max 5 evidence items

    except Exception:
        return []
