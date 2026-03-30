"""Write the conversation exchange to memory."""

from typing import Any, Dict
import logging

from ..state import RouterGraphState

logger = logging.getLogger(__name__)


def write_memory(state: RouterGraphState) -> Dict[str, Any]:
    """Persist the user message + response to the memory system."""
    from app.clients.memory_client import MemoryClient

    user_id = state.get("user_id", "default")
    message = state.get("message", "")
    response = state.get("response", "")
    intent = state.get("intent", "chat")
    emotion_analysis = state.get("emotion_analysis", {})

    if not message or not response:
        return {}

    try:
        client = MemoryClient()
        # Store the exchange as a memory query (triggers memory_write_graph internally)
        exchange = f"User: {message}\nAssistant: {response}"
        context = {"task_type": intent, "app": "jarvis_chat"}
        if emotion_analysis:
            context["emotion"] = emotion_analysis.get("emotion", "neutral")
            context["emotion_valence"] = emotion_analysis.get("valence", 0.0)
            context["emotion_arousal"] = emotion_analysis.get("arousal", 0.3)
            context["emotion_confidence"] = emotion_analysis.get("confidence", 0.0)
        client.query(
            user_id=user_id,
            prompt=exchange,
            context=context,
        )
        client.close()
        logger.debug(f"Wrote conversation to memory for user {user_id}")
    except Exception as e:
        logger.warning(f"Memory write failed (non-blocking): {e}")

    return {}
