"""Vision service configuration."""

import os


class VisionConfig:
    PORT = int(os.getenv("VISION_PORT", "8500"))
    YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n.pt")
    CONFIDENCE_THRESHOLD = float(os.getenv("YOLO_CONFIDENCE", "0.4"))


config = VisionConfig()
