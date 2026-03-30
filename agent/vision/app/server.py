"""Vision API — FastAPI application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from .config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Jarvis Vision API",
    description="Object detection and visual perception",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DetectRequest(BaseModel):
    image_b64: str
    confidence_threshold: Optional[float] = None


@app.get("/health")
def health():
    return {"status": "ok", "service": "jarvis-vision"}


@app.post("/api/detect")
def detect_objects(req: DetectRequest):
    from .detector import detect

    try:
        result = detect(req.image_b64, req.confidence_threshold)
        return result
    except Exception as e:
        logger.error(f"Detection failed: {e}")
        return {"objects": [], "summary": "detection failed", "processing_ms": 0, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
