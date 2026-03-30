import cv2
import numpy as np
from insightface.app import FaceAnalysis

class FaceEngine:
    def __init__(self):
        self.app = FaceAnalysis(name="buffalo_l")
        self.app.prepare(ctx_id=0, det_size=(640, 640))

    def get_embedding(self, image_bytes: bytes) -> np.ndarray:
        np_img = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Invalid image file")

        faces = self.app.get(img)

        if len(faces) == 0:
            raise ValueError("No face detected")

        if len(faces) > 1:
            raise ValueError("Multiple faces detected")

        return faces[0].embedding

    def get_face_data(self, image_bytes: bytes) -> dict:
        np_img = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Invalid image file")

        faces = self.app.get(img)

        if len(faces) == 0:
            raise ValueError("No face detected")

        if len(faces) > 1:
            raise ValueError("Multiple faces detected")

        return {
            "embedding": faces[0].embedding,
            "bbox": faces[0].bbox,
            "image": img,
        }

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))