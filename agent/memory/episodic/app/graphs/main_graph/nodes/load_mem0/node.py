"""
Load Mem0 Node for MainGraph
Node 3: load_mem0

Loads mem0 structured memories from API.
"""

from typing import Dict, Any
from app.shared.types import MainGraphState
from app.shared.normalize import normalize_mem0_items
from app.clients.mem0_client import get_mem0_client


def load_mem0(state: MainGraphState) -> Dict[str, Any]:
    """
    Load mem0 memories from API.

    Args:
        state: Current graph state (must contain user_id)

    Returns:
        State updates with mem0_state, mem0_items, mem0_error, mem0_loaded
    """
    user_id = state.get("user_id")

    if not user_id:
        return {
            "mem0_state": {"items": [], "summary": {"count": 0}},
            "mem0_items": [],
            "mem0_error": "user_id is required",
            "mem0_loaded": False
        }

    try:
        # Get mem0 client
        client = get_mem0_client()

        # Fetch memories
        response = client.get_all(user_id=user_id)

        # Check success
        if not response.get("success", True):
            error_message = response.get("message", "Unknown error")
            return {
                "mem0_state": {"items": [], "summary": {"count": 0, "error": error_message}},
                "mem0_items": [],
                "mem0_error": f"Mem0 API error: {error_message}",
                "mem0_loaded": False
            }

        # Normalize data
        raw_data = response.get("data")
        normalized_items = normalize_mem0_items(raw_data)

        # Build mem0 state
        mem0_state = {
            "items": normalized_items,
            "raw": raw_data,
            "summary": {"count": len(normalized_items)}
        }

        return {
            "mem0_state": mem0_state,
            "mem0_items": normalized_items,
            "mem0_error": None,
            "mem0_loaded": True
        }

    except Exception as e:
        error_message = f"Exception loading mem0: {str(e)}"
        return {
            "mem0_state": {"items": [], "summary": {"count": 0, "error": error_message}},
            "mem0_items": [],
            "mem0_error": error_message,
            "mem0_loaded": False
        }
