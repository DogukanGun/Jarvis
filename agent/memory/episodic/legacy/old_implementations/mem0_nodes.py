"""
Mem0 Nodes for Jarvis MainGraph
Nodes 2-4: mem0_needed (router), load_mem0, use_mem0_state

Handles loading and caching of mem0 structured memory state.
"""

from typing import TypedDict, Optional, List, Dict, Any, Literal
from mem0_client import get_mem0_client, normalize_mem0_items, safe_str


class Mem0State(TypedDict, total=False):
    """Mem0 state structure"""
    items: List[Dict[str, Any]]  # Normalized list of memory items
    raw: Any  # Original raw response for debugging
    summary: Dict[str, Any]  # Summary stats


class GraphState(TypedDict, total=False):
    """Extended graph state for mem0 nodes"""
    # From preprocess_input
    prompt: str
    normalized_prompt: str
    task_type: str
    app: Optional[str]
    entities: List[str]
    preprocess_meta: Dict[str, Any]

    # Context
    context: Optional[Dict[str, Any]]

    # Mem0-related fields
    user_id: str  # Required for mem0 operations
    force_reload_mem0: bool  # Force reload even if cached
    mem0_state: Optional[Mem0State]  # Cached mem0 state
    mem0_items: List[Dict[str, Any]]  # Flattened for easy access
    mem0_error: Optional[str]  # Error message if mem0 load failed
    mem0_loaded: bool  # Whether mem0 was loaded in this run


# Router edge names
MEM0_ROUTE_LOAD = "load"
MEM0_ROUTE_USE = "use"


def mem0_needed_router(state: GraphState) -> Literal["load", "use"]:
    """
    Router node: Decide whether to load mem0 or use existing state.

    Decision logic:
    1. If force_reload_mem0 is True -> LOAD
    2. If mem0_state is missing/None -> LOAD
    3. If mem0_state exists and is valid -> USE

    Args:
        state: Graph state

    Returns:
        "load" or "use"
    """
    # Check force reload flag
    force_reload = state.get("force_reload_mem0", False)
    if force_reload:
        return MEM0_ROUTE_LOAD

    # Check if mem0_state exists and is valid
    mem0_state = state.get("mem0_state")

    if mem0_state is None:
        return MEM0_ROUTE_LOAD

    # Check if state has items (even empty list is valid)
    if "items" not in mem0_state:
        return MEM0_ROUTE_LOAD

    # Valid cached state exists
    return MEM0_ROUTE_USE


def load_mem0(state: GraphState, client=None) -> Dict[str, Any]:
    """
    Load mem0 memories from API.

    Fetches structured memories for the user and normalizes them into state.

    Args:
        state: Graph state (must contain user_id)
        client: Optional client for testing (defaults to get_mem0_client())

    Returns:
        State updates with mem0_state, mem0_items, mem0_error, mem0_loaded
    """
    user_id = state.get("user_id")

    if not user_id:
        return {
            "mem0_state": {"items": [], "raw": None, "summary": {"count": 0}},
            "mem0_items": [],
            "mem0_error": "user_id is required for mem0 operations",
            "mem0_loaded": False,
        }

    # Get client (use injected client for testing, or default factory)
    if client is None:
        client = get_mem0_client()

    try:
        # Fetch memories from API
        response = client.get_all(user_id=user_id)

        # Check if request was successful
        if not response.get("success", True):
            error_message = response.get("message", "Unknown error")
            return {
                "mem0_state": {
                    "items": [],
                    "raw": response.get("data"),
                    "summary": {"count": 0, "error": error_message}
                },
                "mem0_items": [],
                "mem0_error": f"Mem0 API error: {error_message}",
                "mem0_loaded": False,
            }

        # Normalize the data
        raw_data = response.get("data")
        normalized_items = normalize_mem0_items(raw_data)

        # Build mem0 state
        mem0_state: Mem0State = {
            "items": normalized_items,
            "raw": raw_data,
            "summary": {
                "count": len(normalized_items),
                "loaded_at": "timestamp_placeholder",  # Could add actual timestamp
            }
        }

        return {
            "mem0_state": mem0_state,
            "mem0_items": normalized_items,
            "mem0_error": None,
            "mem0_loaded": True,
        }

    except Exception as e:
        # Handle any unexpected errors
        error_message = safe_str(e)
        return {
            "mem0_state": {
                "items": [],
                "raw": None,
                "summary": {"count": 0, "error": error_message}
            },
            "mem0_items": [],
            "mem0_error": f"Exception loading mem0: {error_message}",
            "mem0_loaded": False,
        }


def use_mem0_state(state: GraphState) -> Dict[str, Any]:
    """
    Use existing mem0 state (no API call).

    Reuses cached mem0_state and extracts items for downstream nodes.

    Args:
        state: Graph state (must contain mem0_state)

    Returns:
        State updates with mem0_items extracted from cached state
    """
    mem0_state = state.get("mem0_state")

    if mem0_state is None:
        # This shouldn't happen if router is correct, but handle gracefully
        return {
            "mem0_items": [],
            "mem0_error": "mem0_state is None in use_mem0_state (router error?)",
            "mem0_loaded": False,
        }

    # Extract items from cached state
    items = mem0_state.get("items", [])

    return {
        "mem0_items": items,
        "mem0_error": None,
        "mem0_loaded": False,  # Not loaded in this run (using cache)
    }
