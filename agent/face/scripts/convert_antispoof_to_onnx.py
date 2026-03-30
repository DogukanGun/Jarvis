"""One-time script to convert Silent-Face-Anti-Spoofing PyTorch models to ONNX.

Requires: pip install torch  (only needed at conversion time, not at runtime)

Usage:
    python scripts/convert_antispoof_to_onnx.py
"""

import sys
import os

sys.path.insert(0, "/tmp/Silent-Face-Anti-Spoofing")

import torch
import numpy as np
from pathlib import Path
from src.model_lib.MiniFASNet import MiniFASNetV2, MiniFASNetV1SE
from src.utility import parse_model_name, get_kernel
from collections import OrderedDict

SRC_MODEL_DIR = Path("/tmp/Silent-Face-Anti-Spoofing/resources/anti_spoof_models")
DST_MODEL_DIR = Path(__file__).resolve().parent.parent / "data" / "anti_spoof_models"

MODEL_MAPPING = {
    "MiniFASNetV2": MiniFASNetV2,
    "MiniFASNetV1SE": MiniFASNetV1SE,
}


def convert_model(model_path: Path, output_path: Path):
    model_name = model_path.name
    h_input, w_input, model_type, scale = parse_model_name(model_name)
    kernel_size = get_kernel(h_input, w_input)

    model = MODEL_MAPPING[model_type](conv6_kernel=kernel_size)

    state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
    first_key = next(iter(state_dict))
    if first_key.startswith("module."):
        state_dict = OrderedDict(
            (k[7:], v) for k, v in state_dict.items()
        )
    model.load_state_dict(state_dict)
    model.eval()

    dummy_input = torch.randn(1, 3, h_input, w_input)
    torch.onnx.export(
        model,
        dummy_input,
        str(output_path),
        opset_version=11,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
    )
    print(f"Converted {model_name} -> {output_path.name}  (scale={scale})")


def main():
    DST_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    for pth_file in sorted(SRC_MODEL_DIR.glob("*.pth")):
        onnx_name = pth_file.stem + ".onnx"
        output_path = DST_MODEL_DIR / onnx_name
        convert_model(pth_file, output_path)

    print(f"\nAll models saved to {DST_MODEL_DIR}")


if __name__ == "__main__":
    main()
