"""Face recognition logic — encoding, enrollment, and admin checks."""

import base64
import io
import logging

import face_recognition
import numpy as np
from PIL import Image

from app.config import ADMIN_FILE

logger = logging.getLogger(__name__)


def admin_exists() -> bool:
    return ADMIN_FILE.exists()


def enroll_admin(image_b64: str) -> dict:
    """
    Decode a base64 image, extract the first face encoding, and save it as the admin.
    Returns {"success": True} or {"error": "<reason>"}.
    """
    try:
        img_bytes = base64.b64decode(image_b64)
    except Exception as e:
        return {"error": f"Invalid base64 data: {e}"}

    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        arr = np.array(img)
    except Exception as e:
        return {"error": f"Could not decode image: {e}"}

    encodings = face_recognition.face_encodings(arr)
    if not encodings:
        return {"error": "No face detected in the image"}

    ADMIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(ADMIN_FILE), encodings[0])
    logger.info("Admin face enrolled and saved to %s", ADMIN_FILE)
    return {"success": True}


def delete_admin() -> dict:
    """Remove the saved admin face (dev utility)."""
    if ADMIN_FILE.exists():
        ADMIN_FILE.unlink()
        logger.info("Admin face deleted")
    return {"success": True}
