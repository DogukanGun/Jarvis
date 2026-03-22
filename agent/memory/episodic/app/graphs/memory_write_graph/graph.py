"""
Memory Write Graph Definition

Wires together all nodes of the async memory write pipeline.
"""

from langgraph.graph import StateGraph, END
import logging

from .state import MemoryWriteState
from .nodes import (
    build_episode_candidates,
    gate_action,
    redact_secrets,
    fingerprint_node,
    dedupe_lookup,
    insert_episode,
    reinforce_episode,
    embed_episode,
    promote_check,
    create_promotion_proposal,
)

logger = logging.getLogger(__name__)


def create_memory_write_graph():
    """
    Create and configure the memory_write_graph.

    Flow:
    1. build_episode_candidates - Filter meaningful items
    2. gate_action - Route: save/ignore/save_and_promote
    3. redact_secrets - Mask sensitive data
    4. fingerprint - Generate hash
    5. dedupe_lookup - Check for existing episode
    6. insert_episode OR reinforce_episode
    7. embed_episode - Generate embedding
    8. promote_check - Check promotion criteria
    9. create_promotion_proposal (if promoted)

    Returns:
        Compiled LangGraph
    """
    graph = StateGraph(MemoryWriteState)

    # Add all nodes
    graph.add_node("build_episode_candidates", build_episode_candidates)
    graph.add_node("redact_secrets", redact_secrets)
    graph.add_node("fingerprint", fingerprint_node)
    graph.add_node("dedupe_lookup", dedupe_lookup)
    graph.add_node("insert_episode", insert_episode)
    graph.add_node("reinforce_episode", reinforce_episode)
    graph.add_node("embed_episode", embed_episode)
    graph.add_node("create_promotion_proposal", create_promotion_proposal)

    # Noop nodes for routing
    graph.add_node("noop", lambda state: {"completed": True})
    graph.add_node("end_no_promotion", lambda state: {"completed": True, "should_promote": False})

    # Entry point
    graph.set_entry_point("build_episode_candidates")

    # Gate action: conditional edge from build_episode_candidates
    graph.add_conditional_edges(
        "build_episode_candidates",
        gate_action,
        {
            "save": "redact_secrets",
            "save_and_promote": "redact_secrets",
            "ignore": "noop"
        }
    )

    # Noop -> END
    graph.add_edge("noop", END)

    # Linear flow: redact -> fingerprint -> dedupe
    graph.add_edge("redact_secrets", "fingerprint")
    graph.add_edge("fingerprint", "dedupe_lookup")

    # is_duplicate? conditional edge
    def is_duplicate_router(state: MemoryWriteState) -> str:
        return "yes" if state.get("is_duplicate") else "no"

    graph.add_conditional_edges(
        "dedupe_lookup",
        is_duplicate_router,
        {
            "yes": "reinforce_episode",
            "no": "insert_episode"
        }
    )

    # Both paths converge to embed_episode
    graph.add_edge("insert_episode", "embed_episode")
    graph.add_edge("reinforce_episode", "embed_episode")

    # promote_check? conditional edge
    graph.add_conditional_edges(
        "embed_episode",
        promote_check,
        {
            "yes": "create_promotion_proposal",
            "no": "end_no_promotion"
        }
    )

    # Terminal nodes
    graph.add_edge("create_promotion_proposal", END)
    graph.add_edge("end_no_promotion", END)

    return graph.compile()


# Create default instance
memory_write_graph = create_memory_write_graph()


def run_memory_write_graph(payload: dict) -> MemoryWriteState:
    """
    Run the memory_write_graph end-to-end.

    Args:
        payload: Memory write payload from MainGraph

    Returns:
        Final state after graph execution
    """
    initial_state: MemoryWriteState = {
        "user_id": payload.get("user_id"),
        "task_type": payload.get("task_type"),
        "app": payload.get("app"),
        "entities": payload.get("entities", []),
        "prompt": payload.get("prompt", ""),
        "llm_output": payload.get("llm_output"),
        "memory_intents": payload.get("memory_intents"),
        "timestamp": payload.get("timestamp", ""),
        "errors": []
    }

    from app.monitor import get_monitor
    import time

    monitor = get_monitor()
    monitor.emit("graph_run_start", {"graph": "memory_write_graph", "user_id": payload.get("user_id")})
    t0 = time.time()

    try:
        result = memory_write_graph.invoke(initial_state)
        duration_ms = round((time.time() - t0) * 1000)
        monitor.emit("graph_run_end", {"graph": "memory_write_graph", "duration_ms": duration_ms})
        monitor.emit("write_completed", {"latency_ms": duration_ms})
        logger.info(f"Memory write completed for user {payload.get('user_id')}")
        return result
    except Exception as e:
        monitor.emit("graph_run_error", {"graph": "memory_write_graph", "error": str(e)})
        logger.error(f"Memory write graph error: {str(e)}")
        initial_state["errors"] = [str(e)]
        initial_state["completed"] = False
        return initial_state
