"""
MainGraph Definition

Wires together all 9 nodes of the MainGraph using LangGraph.
"""

from langgraph.graph import StateGraph, END

from .state import MainGraphState
from .nodes.preprocess_input import preprocess_input
from .nodes.mem0_needed import mem0_needed
from .nodes.load_mem0 import load_mem0
from .nodes.use_mem0_state import use_mem0_state
from .nodes.retrieve_episodes import retrieve_episodes
from .nodes.compose_context import compose_context
from .nodes.llm_step import llm_step
from .nodes.return_output import return_output
from .nodes.enqueue_memory_write_graph import enqueue_memory_write_graph


def create_main_graph():
    """
    Create and configure the MainGraph.

    Flow:
    1. preprocess_input
    2. mem0_needed (router) -> load_mem0 OR use_mem0_state
    3. retrieve_episodes
    4. compose_context
    5. llm_step
    6. return_output
    7. enqueue_memory_write_graph
    8. END

    Returns:
        Compiled LangGraph
    """
    # Create graph
    graph = StateGraph(MainGraphState)

    # Add all nodes
    graph.add_node("preprocess_input", preprocess_input)
    graph.add_node("load_mem0", load_mem0)
    graph.add_node("use_mem0_state", use_mem0_state)
    graph.add_node("retrieve_episodes", retrieve_episodes)
    graph.add_node("compose_context", compose_context)
    graph.add_node("llm_step", llm_step)
    graph.add_node("return_output", return_output)
    graph.add_node("enqueue_memory_write_graph", enqueue_memory_write_graph)

    # Set entry point
    graph.set_entry_point("preprocess_input")

    # Connect preprocess to mem0 router
    graph.add_conditional_edges(
        "preprocess_input",
        mem0_needed,
        {
            "load": "load_mem0",
            "use": "use_mem0_state"
        }
    )

    # Both mem0 paths converge to retrieve_episodes
    graph.add_edge("load_mem0", "retrieve_episodes")
    graph.add_edge("use_mem0_state", "retrieve_episodes")

    # Linear flow after retrieval
    graph.add_edge("retrieve_episodes", "compose_context")
    graph.add_edge("compose_context", "llm_step")
    graph.add_edge("llm_step", "return_output")
    graph.add_edge("return_output", "enqueue_memory_write_graph")

    # End after enqueue
    graph.add_edge("enqueue_memory_write_graph", END)

    # Compile and return
    return graph.compile()


# Create default instance
main_graph = create_main_graph()


def run_main_graph(user_id: str, prompt: str, context: dict = None) -> MainGraphState:
    """
    Run the MainGraph end-to-end.

    Args:
        user_id: User identifier
        prompt: User prompt
        context: Optional context dict

    Returns:
        Final state after graph execution
    """
    from app.monitor import get_monitor
    import time

    monitor = get_monitor()
    initial_state: MainGraphState = {
        "user_id": user_id,
        "prompt": prompt,
        "context": context or {}
    }

    monitor.emit("graph_run_start", {"graph": "main_graph", "user_id": user_id})
    t0 = time.time()

    try:
        result = main_graph.invoke(initial_state)
        duration_ms = round((time.time() - t0) * 1000)
        monitor.emit("graph_run_end", {"graph": "main_graph", "duration_ms": duration_ms})
        return result
    except Exception as e:
        monitor.emit("graph_run_error", {"graph": "main_graph", "error": str(e)})
        raise
