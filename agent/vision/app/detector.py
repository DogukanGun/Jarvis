"""YOLO object detection wrapper."""

import base64
import io
import time
import logging

from PIL import Image
from ultralytics import YOLO

from .config import config

logger = logging.getLogger(__name__)

# Load model once at module level
_model = YOLO(config.YOLO_MODEL)
logger.info(f"Loaded YOLO model: {config.YOLO_MODEL}")


def detect(image_b64: str, confidence: float = None) -> dict:
    """Run object detection on a base64-encoded image.

    Returns:
        {
            "objects": [{"label": str, "confidence": float, "bbox": [x1,y1,x2,y2]}, ...],
            "summary": "person, laptop, cup",
            "processing_ms": int
        }
    """
    if confidence is None:
        confidence = config.CONFIDENCE_THRESHOLD

    # Decode base64 to PIL Image
    image_bytes = base64.b64decode(image_b64)
    image = Image.open(io.BytesIO(image_bytes))

    t0 = time.time()
    results = _model.predict(source=image, conf=confidence, verbose=False)
    processing_ms = round((time.time() - t0) * 1000)

    objects = []
    seen_labels = set()

    for result in results:
        for box in result.boxes:
            label = result.names[int(box.cls[0])]
            conf = float(box.conf[0])
            bbox = box.xyxy[0].tolist()

            objects.append({
                "label": label,
                "confidence": round(conf, 3),
                "bbox": [round(v, 1) for v in bbox],
            })
            seen_labels.add(label)

    # Sort by confidence descending
    objects.sort(key=lambda o: o["confidence"], reverse=True)

    summary = ", ".join(sorted(seen_labels)) if seen_labels else "nothing detected"

    logger.info(f"Detected {len(objects)} objects in {processing_ms}ms: {summary}")

    return {
        "objects": objects,
        "summary": summary,
        "processing_ms": processing_ms,
    }
