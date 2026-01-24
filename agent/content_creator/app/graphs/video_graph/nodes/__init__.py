"""Video graph nodes."""
from app.graphs.video_graph.nodes.load_model import load_model_node
from app.graphs.video_graph.nodes.generate_frames import (
    generate_frames_node,
    generation_router,
)
from app.graphs.video_graph.nodes.encode_video import encode_video_node, encode_router
from app.graphs.video_graph.nodes.upload_result import upload_result_node
from app.graphs.video_graph.nodes.publish_result import publish_result_node
from app.graphs.video_graph.nodes.handle_error import handle_error_node

__all__ = [
    "load_model_node",
    "generate_frames_node",
    "generation_router",
    "encode_video_node",
    "encode_router",
    "upload_result_node",
    "publish_result_node",
    "handle_error_node",
]
