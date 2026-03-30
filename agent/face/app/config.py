"""Face API configuration."""

import os
from pathlib import Path

PORT = int(os.getenv("PORT", "8400"))
DATA_DIR = Path(os.getenv("FACE_DATA_DIR", "data"))
ADMIN_FILE = DATA_DIR / "admin_face.npy"
ANTI_SPOOF_MODEL_DIR = DATA_DIR / "anti_spoof_models"
ANTI_SPOOF_THRESHOLD = float(os.getenv("ANTI_SPOOF_THRESHOLD", "0.5"))
