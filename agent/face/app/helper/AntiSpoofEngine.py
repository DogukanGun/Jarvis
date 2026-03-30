"""Face anti-spoofing (liveness detection) using Silent-Face-Anti-Spoofing ONNX models."""

import cv2
import numpy as np
import onnxruntime as ort
from pathlib import Path


def _parse_model_name(model_name: str):
    """Parse scale, height, width from model filename.

    Matches Silent-Face-Anti-Spoofing naming convention:
      '2.7_80x80_MiniFASNetV2.onnx' -> (80, 80, 2.7)
      '4_0_0_80x80_MiniFASNetV1SE.onnx' -> (80, 80, 4.0)
    """
    stem = model_name.split(".onnx")[0]
    parts = stem.split("_")
    # The original parser uses info[0] as scale
    scale = float(parts[0])
    # Find the dimension part (e.g. "80x80")
    for part in parts:
        if "x" in part and part[0].isdigit():
            h_input, w_input = part.split("x")
            return int(h_input), int(w_input), scale
    raise ValueError(f"Cannot parse model name: {model_name}")


def _crop_face(image: np.ndarray, bbox, scale: float, out_h: int, out_w: int) -> np.ndarray:
    """Crop face region with scale expansion (matches Silent-Face-Anti-Spoofing CropImage)."""
    src_h, src_w = image.shape[:2]
    x, y, box_w, box_h = bbox

    scale = min((src_h - 1) / box_h, min((src_w - 1) / box_w, scale))

    new_width = box_w * scale
    new_height = box_h * scale
    center_x = box_w / 2 + x
    center_y = box_h / 2 + y

    left_top_x = center_x - new_width / 2
    left_top_y = center_y - new_height / 2
    right_bottom_x = center_x + new_width / 2
    right_bottom_y = center_y + new_height / 2

    if left_top_x < 0:
        right_bottom_x -= left_top_x
        left_top_x = 0
    if left_top_y < 0:
        right_bottom_y -= left_top_y
        left_top_y = 0
    if right_bottom_x > src_w - 1:
        left_top_x -= right_bottom_x - src_w + 1
        right_bottom_x = src_w - 1
    if right_bottom_y > src_h - 1:
        left_top_y -= right_bottom_y - src_h + 1
        right_bottom_y = src_h - 1

    cropped = image[int(left_top_y):int(right_bottom_y) + 1,
                    int(left_top_x):int(right_bottom_x) + 1]
    return cv2.resize(cropped, (out_w, out_h))


def _softmax(x: np.ndarray) -> np.ndarray:
    e_x = np.exp(x - np.max(x, axis=1, keepdims=True))
    return e_x / np.sum(e_x, axis=1, keepdims=True)


class AntiSpoofEngine:
    def __init__(self, model_dir: Path):
        self.models = []
        for onnx_file in sorted(model_dir.glob("*.onnx")):
            h_input, w_input, scale = _parse_model_name(onnx_file.name)
            session = ort.InferenceSession(
                str(onnx_file),
                providers=["CPUExecutionProvider"],
            )
            self.models.append({
                "session": session,
                "h_input": h_input,
                "w_input": w_input,
                "scale": scale,
                "input_name": session.get_inputs()[0].name,
            })
        if not self.models:
            raise FileNotFoundError(f"No ONNX models found in {model_dir}")

    def check_liveness(self, image: np.ndarray, bbox: np.ndarray, threshold: float = 0.5) -> tuple:
        """Check if the face is real.

        Args:
            image: Decoded BGR image (numpy array from cv2).
            bbox: Face bounding box [x1, y1, x2, y2] from InsightFace.
            threshold: Confidence threshold for real face (default 0.5).

        Returns:
            (is_live: bool, confidence: float)
        """
        # Convert InsightFace bbox [x1, y1, x2, y2] to [x, y, w, h]
        x1, y1, x2, y2 = [int(v) for v in bbox]
        bbox_xywh = [x1, y1, x2 - x1, y2 - y1]

        prediction = np.zeros((1, 3))

        for model in self.models:
            cropped = _crop_face(
                image, bbox_xywh, model["scale"],
                model["h_input"], model["w_input"],
            )
            # Preprocess: keep [0, 255] range (model was trained without /255), transpose to NCHW
            inp = cropped.astype(np.float32)
            inp = np.transpose(inp, (2, 0, 1))  # HWC -> CHW
            inp = np.expand_dims(inp, axis=0)    # add batch dim

            output = model["session"].run(None, {model["input_name"]: inp})[0]
            prediction += _softmax(output)

        # Average across models; class 1 = real face
        prediction /= len(self.models)
        label = np.argmax(prediction)
        confidence = float(prediction[0][1])  # real face probability

        is_live = label == 1 and confidence >= threshold
        return is_live, confidence
