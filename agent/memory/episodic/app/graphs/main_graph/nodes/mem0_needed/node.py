"""
Mem0 Needed Router Node for MainGraph
Node 2: mem0_needed (router)

Decides whether to load mem0 from API or use cached state.
"""

from typing import Literal
from app.shared.types import MainGraphState


def mem0_needed(state: MainGraphState) -> Literal["load", "use"]:
    """
    Router to decide: load mem0 or use cached state.

    Decision logic:
    1. If force_mem0_reload = True -> load
    2. If mem0_state is None -> load
    3. If mem0_state exists -> use

    Args:
        state: Current graph state

    Returns:
        "load" or "use"
    """
    # Check force reload
    if state.get("force_mem0_reload", False):
        return "load"

    # Check if mem0_state exists
    mem0_state = state.get("mem0_state")
    if mem0_state is None:
        return "load"

    # Check if state has items key
    if "items" not in mem0_state:
        return "load"

    # Valid cache exists
    return "use"
