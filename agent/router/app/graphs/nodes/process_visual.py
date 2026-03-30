"""Process visual feed data through registered handlers."""
from typing import Any, Dict, Callable
import logging
from ..state import RouterGraphState

logger = logging.getLogger(__name__)

_HANDLERS: Dict[tuple, Callable] = {}


def register_handler(source: str, way: str):
    def decorator(fn):
        _HANDLERS[(source, way)] = fn
        return fn
    return decorator


@register_handler("desktop", "yolo")
def _handle_desktop_yolo(feed_data: dict) -> dict:
    from app.clients.vision_client import VisionClient
    frame_b64 = feed_data.get("frame_b64", "")
    if not frame_b64:
        return None
    try:
        client = VisionClient()
        result = client.detect(frame_b64)
        client.close()
        return {
            "objects": result.get("objects", []),
            "summary": result.get("summary", ""),
            "source": "desktop",
            "way": "yolo",
        }
    except Exception as e:
        logger.error(f"Desktop YOLO detection failed: {e}")
        return None


def process_visual(state: RouterGraphState) -> Dict[str, Any]:
    feed = state.get("visual_feed")
    if not feed:
        return {}
    source = feed.get("source", "")
    way = feed.get("way", "")
    handler = _HANDLERS.get((source, way))
    if handler is None:
        logger.warning(f"No visual handler for source={source}, way={way}")
        return {}
    try:
        ctx = handler(feed.get("data", {}))
        if ctx:
            logger.info(f"Visual context: {ctx.get('summary', '')}")
            return {"visual_context": ctx}
    except Exception as e:
        logger.error(f"Visual processing failed: {e}")
    return {}
