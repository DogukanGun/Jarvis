"""Image reference graph nodes."""
from app.graphs.image_reference_graph.nodes.download_reference import (
    download_reference_node,
    download_router,
)
from app.graphs.image_reference_graph.nodes.load_model import load_model_node
from app.graphs.image_reference_graph.nodes.generate import generate_node, generation_router
from app.graphs.image_reference_graph.nodes.upload_result import upload_result_node
from app.graphs.image_reference_graph.nodes.publish_result import publish_result_node
from app.graphs.image_reference_graph.nodes.handle_error import handle_error_node

__all__ = [
    "download_reference_node",
    "download_router",
    "load_model_node",
    "generate_node",
    "generation_router",
    "upload_result_node",
    "publish_result_node",
    "handle_error_node",
]
