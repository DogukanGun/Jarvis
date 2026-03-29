"""Face API configuration."""

import os
from pathlib import Path

PORT = int(os.getenv("PORT", "8400"))
DATA_DIR = Path(os.getenv("FACE_DATA_DIR", "data"))
ADMIN_FILE = DATA_DIR / "admin_face.npy"
