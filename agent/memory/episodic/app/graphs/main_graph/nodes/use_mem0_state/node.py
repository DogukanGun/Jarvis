"""
Use Mem0 State Node for MainGraph
Node 4: use_mem0_state

Reuses cached mem0 state without API call.
"""

from typing import Dict, Any
from app.shared.types import MainGraphState


def use_mem0_state(state: MainGraphState) -> Dict[str, Any]:
    """
    Use cached mem0 state.

    Args:
        state: Current graph state (must contain mem0_state)

    Returns:
        State updates with mem0_items extracted from cache
    """
    mem0_state = state.get("mem0_state")

    if mem0_state is None:
        return {
            "mem0_items": [],
            "mem0_error": "mem0_state is None (router error?)",
            "mem0_loaded": False
        }

    # Extract items from cache
    items = mem0_state.get("items", [])

    return {
        "mem0_items": items,
        "mem0_error": None,
        "mem0_loaded": False  # Not loaded this run (using cache)
    }
