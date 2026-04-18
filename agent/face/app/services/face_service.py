"""Face recognition logic — encoding, enrollment, and admin checks."""

import logging
import numpy as np
from app.config import ADMIN_FILE, ANTI_SPOOF_MODEL_DIR, ANTI_SPOOF_THRESHOLD
from app.helper import FaceEngine, AntiSpoofEngine

logger = logging.getLogger(__name__)

engine = FaceEngine()
anti_spoof = AntiSpoofEngine(ANTI_SPOOF_MODEL_DIR)
threshold = 0.4  # insightface buffalo_l: same-person cosine similarity is typically 0.3-0.5


def _check_liveness(image, bbox):
    """Run anti-spoofing check; raises ValueError if face is not live."""
    is_live, confidence = anti_spoof.check_liveness(image, bbox, ANTI_SPOOF_THRESHOLD)
    logger.info(f"Liveness check: is_live={is_live}, confidence={confidence:.4f}, threshold={ANTI_SPOOF_THRESHOLD}")
    if not is_live:
        raise ValueError(
            f"Liveness check failed (confidence: {confidence:.2f}). "
            "Please use a real face, not a photo or screen."
        )


class FaceRecognitionService:

    @staticmethod
    def admin_exists() -> bool:
        return ADMIN_FILE.exists()

    @staticmethod
    def is_admin(image_bytes: bytes) -> bool:
        face_data = engine.get_face_data(image_bytes)
        _check_liveness(face_data["image"], face_data["bbox"])
        saved_embedding = np.load(ADMIN_FILE)
        similarity = engine.cosine_similarity(saved_embedding, face_data["embedding"])
        logger.info(f"Face similarity: {similarity:.4f} (threshold: {threshold})")
        return similarity >= threshold

    @staticmethod
    def enroll_admin(image_bytes: bytes) -> bool:
        face_data = engine.get_face_data(image_bytes)
        _check_liveness(face_data["image"], face_data["bbox"])
        np.save(ADMIN_FILE, face_data["embedding"])
        return True

    @staticmethod
    def delete_admin() -> bool:
        """Remove the saved admin face (dev utility)."""
        if ADMIN_FILE.exists():
            ADMIN_FILE.unlink()
            logger.info("Admin face deleted")
        return True
