"""
Create Promotion Proposals Node

Creates promotion proposals from resolved patterns.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging

from ..state import ReflectionState
from app.storage import get_episode_repository, PromotionProposal

logger = logging.getLogger(__name__)


def create_promotion_proposals(state: ReflectionState) -> Dict[str, Any]:
    """
    Create promotion proposals for high-confidence patterns.

    Args:
        state: Current graph state

    Returns:
        State updates with proposals_created
    """
    from app.config import config

    patterns = state.get("resolved_patterns", [])
    user_id = state.get("user_id")

    if not patterns:
        return {
            "proposals_created": [],
            "proposals_count": 0,
            "completed": True
        }

    try:
        repo = get_episode_repository()
        proposals_created: List[str] = []

        for pattern in patterns:
            # Check confidence threshold
            if pattern.get("confidence", 0) < config.PROMOTION_MIN_CONFIDENCE:
                logger.debug(f"Skipping low confidence pattern: {pattern.get('confidence')}")
                continue

            # Create proposal
            proposal = _create_proposal_from_pattern(pattern, user_id, config)

            # Store proposal
            proposal_id = repo.insert_proposal(proposal)
            proposals_created.append(proposal_id)

            logger.info(f"Created proposal {proposal_id} from reflection")

        logger.info(f"Created {len(proposals_created)} proposals from {len(patterns)} patterns")

        return {
            "proposals_created": proposals_created,
            "proposals_count": len(proposals_created),
            "completed": True
        }

    except Exception as e:
        error_msg = f"Proposal creation error: {str(e)}"
        logger.error(error_msg)
        return {
            "proposals_created": [],
            "proposals_count": 0,
            "completed": True,
            "errors": state.get("errors", []) + [error_msg]
        }


def _create_proposal_from_pattern(
    pattern: Dict[str, Any],
    user_id: str,
    config
) -> PromotionProposal:
    """
    Create a PromotionProposal from a detected pattern.
    """
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=config.KAFKA_APPROVAL_TIMEOUT_SECONDS)

    # Build proposed value
    proposed_value = _build_proposed_value(pattern)

    # Use first episode as reference
    episode_ids = pattern.get("episode_ids", [])
    episode_id = episode_ids[0] if episode_ids else None

    return PromotionProposal(
        episode_id=episode_id,
        user_id=user_id,
        target_path=_suggest_target_path(pattern),
        proposed_value=proposed_value,
        confidence=pattern.get("confidence", 0.5),
        evidence=episode_ids[:5],  # Max 5 evidence items
        status="pending",
        created_at=now,
        expires_at=expires_at
    )


def _build_proposed_value(pattern: Dict[str, Any]) -> str:
    """
    Build human-readable proposed value from pattern.
    """
    summary = pattern.get("representative_summary")
    if summary:
        return summary

    task_type = pattern.get("task_type")
    app = pattern.get("app")
    count = pattern.get("total_reinforcement", pattern.get("count", 1))

    if task_type and app:
        return f"User frequently performs {task_type} tasks using {app} ({count} occurrences)"
    elif task_type:
        return f"User frequently performs {task_type} tasks ({count} occurrences)"
    elif app:
        return f"User frequently uses {app} ({count} occurrences)"

    # Fallback to representative text
    text = pattern.get("representative_text", "")
    if len(text) > 150:
        return text[:147] + "..."
    return text


def _suggest_target_path(pattern: Dict[str, Any]) -> str:
    """
    Suggest target path in mem0 for the pattern.
    """
    task_type = pattern.get("task_type")
    app = pattern.get("app")

    if task_type:
        return f"patterns.{task_type}"
    elif app:
        return f"apps.{app}"
    else:
        return "patterns.general"
