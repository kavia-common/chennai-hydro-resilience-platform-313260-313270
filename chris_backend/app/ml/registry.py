from __future__ import annotations

from app.core.settings import settings
from app.ml.model_a import ModelAArtifacts, load_model_a_onnx
from app.ml.model_b import ModelBArtifacts, load_model_b_onnx

MODEL_A: ModelAArtifacts | None = None
MODEL_B: ModelBArtifacts | None = None


def load_all() -> None:
    global MODEL_A, MODEL_B

    if settings.chris_model_a_provider.lower() == "onnx":
        MODEL_A = load_model_a_onnx(
            onnx_path=settings.chris_model_a_path,
            meta_path=settings.chris_model_a_meta_path,
            scaler_x_path=settings.chris_model_a_scaler_x_path,
            scaler_y_path=settings.chris_model_a_scaler_y_path,
        )

    if settings.chris_model_b_provider.lower() == "onnx":
        MODEL_B = load_model_b_onnx(
            onnx_path=settings.chris_model_b_path,
            meta_path=settings.chris_model_b_meta_path,
        )
