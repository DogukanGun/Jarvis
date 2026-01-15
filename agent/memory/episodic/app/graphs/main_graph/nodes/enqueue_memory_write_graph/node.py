"""
Enqueue Memory Write Graph Node for MainGraph
Node 9: enqueue_memory_write_graph

Creates payload and dispatches async memory write to memory_write_graph.
This uses the two-tier memory system (episodic SQLite + long-term mem0).
"""

from typing import Dict, Any
import logging
import threading
from datetime import datetime
from app.shared.types import MainGraphState

logger = logging.getLogger(__name__)


def enqueue_memory_write_graph(state: MainGraphState) -> Dict[str, Any]:
    """
    Build and dispatch payload for memory write.

    This is a non-blocking operation - memory writes happen
    in a background thread so the user response is not delayed.

    The payload is dispatched to memory_write_graph which handles:
    1. Building episode candidates
    2. Secret redaction
    3. Fingerprinting for deduplication
    4. Inserting new or reinforcing existing episodes
    5. Embedding generation
    6. Promotion check (episodes → mem0)

    Args:
        state: Current graph state

    Returns:
        State updates with memory_job_payload, enqueue_error
    """
    try:
        from app.config import config
        if not config.ENABLE_MEMORY_WRITE:
            logger.info("Memory write disabled, skipping enqueue")
            return {
                "memory_job_payload": None,
                "enqueue_error": None
            }

        user_id = state.get("user_id")
        if not user_id:
            return {
                "memory_job_payload": None,
                "enqueue_error": "user_id required for memory write"
            }

        # Build payload for memory_write_graph
        memory_job_payload = {
            "user_id": user_id,
            "task_type": state.get("task_type"),
            "app": state.get("app"),
            "entities": state.get("entities", []),
            "prompt": state.get("normalized_prompt", state.get("prompt", "")),
            "llm_output": state.get("llm_output"),
            "memory_intents": state.get("memory_intents"),
            "timestamp": datetime.utcnow().isoformat(),
            # Additional context for episodic storage
            "importance_score": state.get("importance_score"),
            "conversation_id": state.get("conversation_id"),
        }

        # Dispatch to background thread (non-blocking)
        thread = threading.Thread(
            target=_execute_memory_write_graph,
            args=(memory_job_payload,),
            daemon=True
        )
        thread.start()

        logger.info(f"Dispatched memory_write_graph job for user: {user_id}")

        return {
            "memory_job_payload": memory_job_payload,
            "enqueue_error": None
        }

    except Exception as e:
        error_message = f"Enqueue error: {str(e)}"
        logger.error(error_message)
        return {
            "memory_job_payload": None,
            "enqueue_error": error_message
        }


def _execute_memory_write_graph(payload: Dict[str, Any]) -> None:
    """
    Execute memory_write_graph in background.

    Invokes the full memory write pipeline:
    - Episode candidate creation
    - Secret redaction
    - Fingerprinting & deduplication
    - SQLite storage (insert/reinforce)
    - Embedding generation
    - Promotion check & proposal creation

    Args:
        payload: Memory job payload from MainGraph
    """
    try:
        from app.graphs.memory_write_graph import run_memory_write_graph
        from app.graphs.memory_write_graph.state import MemoryWriteState

        user_id = payload["user_id"]
        prompt = payload.get("prompt", "")
        llm_output = payload.get("llm_output", "")

        # Skip if no meaningful content
        if not prompt or not llm_output:
            logger.debug("Skipping memory write - no content")
            return

        # Build initial state for memory_write_graph
        initial_state: MemoryWriteState = {
            "user_id": user_id,
            "prompt": prompt,
            "llm_output": str(llm_output),
            "task_type": payload.get("task_type"),
            "app": payload.get("app"),
            "entities": payload.get("entities", []),
            "memory_intents": payload.get("memory_intents"),
            "importance_score": payload.get("importance_score"),
            "conversation_id": payload.get("conversation_id"),
            "timestamp": payload.get("timestamp"),
            "errors": []
        }

        # Run memory_write_graph
        result = run_memory_write_graph(initial_state)

        if result.get("completed"):
            episode_id = result.get("episode_id")
            action = result.get("action")
            if episode_id:
                logger.info(f"Memory write completed: {action} episode {episode_id} for user {user_id}")
            else:
                logger.info(f"Memory write completed: action={action} for user {user_id}")

            # Check if promotion proposal was created
            if result.get("promotion_proposal_id"):
                logger.info(f"Promotion proposal created: {result['promotion_proposal_id']}")
        else:
            errors = result.get("errors", [])
            logger.warning(f"Memory write incomplete: {errors}")

    except Exception as e:
        logger.error(f"Memory write graph error: {str(e)}")
