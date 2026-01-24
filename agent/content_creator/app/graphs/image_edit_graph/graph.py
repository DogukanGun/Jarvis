"""
Image Edit Graph.

Edits images based on prompts using Qwen-Image-Edit-2511.

Flow:
    START -> download_source --(success)--> load_model -> edit --(success)--> upload_result -> publish_result -> END
                   |                                        |
                (error)                                  (error)
                   v                                        v
              handle_error <--------------------------------+
"""
import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, END

from app.graphs.image_edit_graph.state import ImageEditGraphState
from app.graphs.image_edit_graph.nodes import (
    download_source_node,
    download_router,
    load_model_node,
    edit_node,
    edit_router,
    upload_result_node,
    publish_result_node,
    handle_error_node,
)

logger = logging.getLogger(__name__)


def create_image_edit_graph() -> StateGraph:
    """
    Create and compile the Image Edit Graph.

    Returns:
        Compiled LangGraph ready for execution.
    """
    logger.info("Creating Image Edit graph...")

    graph = StateGraph(ImageEditGraphState)

    # Add nodes
    graph.add_node("download_source", download_source_node)
    graph.add_node("load_model", load_model_node)
    graph.add_node("edit", edit_node)
    graph.add_node("upload_result", upload_result_node)
    graph.add_node("publish_result", publish_result_node)
    graph.add_node("handle_error", handle_error_node)

    # Set entry point
    graph.set_entry_point("download_source")

    # Add edges
    graph.add_conditional_edges(
        "download_source",
        download_router,
        {
            "load": "load_model",
            "error": "handle_error",
        }
    )

    graph.add_edge("load_model", "edit")

    graph.add_conditional_edges(
        "edit",
        edit_router,
        {
            "upload": "upload_result",
            "error": "handle_error",
        }
    )

    graph.add_edge("upload_result", "publish_result")
    graph.add_edge("publish_result", END)
    graph.add_edge("handle_error", END)

    compiled = graph.compile()
    logger.info("Image Edit graph compiled successfully")

    return compiled


def run_image_edit_graph(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the Image Edit Graph with the given request.

    Args:
        request: Parsed RenderRequest dict

    Returns:
        Final graph state
    """
    job_id = request.get("job_id", "unknown")
    logger.info(f"Processing image edit request: {job_id}")

    graph = create_image_edit_graph()

    initial_state: ImageEditGraphState = {
        "request": request,
        "job_id": job_id,
    }

    try:
        result = graph.invoke(initial_state)
        logger.info(f"Image Edit graph completed for job {job_id}")
        return result
    except Exception as e:
        logger.error(f"Image Edit graph failed: {str(e)}")
        raise
