from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image

from app.ml.onnx_runtime import OnnxModel, load_onnx_model, run_onnx


@dataclass
class ModelBMeta:
    input_size: int = 256
    classes: dict[str, str] | None = None


@dataclass
class ModelBArtifacts:
    provider: str
    meta: ModelBMeta
    onnx: OnnxModel | None = None


def load_model_b_onnx(onnx_path: str, meta_path: str) -> ModelBArtifacts:
    meta_raw = json.load(open(meta_path, "r"))
    meta = ModelBMeta(
        input_size=int((meta_raw.get("input") or {}).get("shape", [256, 256, 3])[0]),
        classes=meta_raw.get("classes"),
    )
    onnx_model = load_onnx_model(onnx_path)
    return ModelBArtifacts(provider="onnx", meta=meta, onnx=onnx_model)


def preprocess_image_rgb(image_bytes: bytes, size: int) -> np.ndarray:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((size, size))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return arr[np.newaxis, :, :, :]


import io  # keep at bottom to avoid lint reorder noise


def predict_segmentation(art: ModelBArtifacts, image_bytes: bytes) -> dict[str, Any]:
    if art.provider != "onnx" or art.onnx is None:
        raise RuntimeError("Only ONNX provider is currently wired in this repo.")

    x = preprocess_image_rgb(image_bytes, art.meta.input_size).astype(np.float32)
    outputs = run_onnx(art.onnx, x)
    y = list(outputs.values())[0]  # (1,H,W,C) expected
    y = np.asarray(y)
    mask = np.argmax(y, axis=-1)[0].astype(np.int32)  # (H,W)

    # simple proportions
    unique, counts = np.unique(mask, return_counts=True)
    total = float(mask.size)
    proportions = {str(int(k)): float(v) / total for k, v in zip(unique, counts, strict=False)}

    return {"mask": mask.tolist(), "proportions": proportions}
