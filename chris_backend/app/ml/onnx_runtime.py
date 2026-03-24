from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import onnxruntime as ort


@dataclass
class OnnxModel:
    session: ort.InferenceSession
    input_name: str
    output_names: list[str]


def load_onnx_model(path: str, preferred_providers: list[str] | None = None) -> OnnxModel:
    providers = preferred_providers or ["CPUExecutionProvider"]
    sess = ort.InferenceSession(path, providers=providers)
    input_name = sess.get_inputs()[0].name
    output_names = [o.name for o in sess.get_outputs()]
    return OnnxModel(session=sess, input_name=input_name, output_names=output_names)


def run_onnx(model: OnnxModel, x: np.ndarray) -> dict[str, Any]:
    outputs = model.session.run(model.output_names, {model.input_name: x})
    return {name: arr for name, arr in zip(model.output_names, outputs, strict=False)}
