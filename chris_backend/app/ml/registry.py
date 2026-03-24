from __future__ import annotations

from app.core.settings import settings
from app.ml.model_a import ModelAArtifacts, load_model_a_onnx
from app.ml.model_b import ModelBArtifacts, load_model_b_onnx

MODEL_A: ModelAArtifacts | None = None
MODEL_B: ModelBArtifacts | None = None

# Captures load errors without preventing other models from loading.
# Keys: "model_a", "model_b"
LOAD_ERRORS: dict[str, str] = {}


# PUBLIC_INTERFACE
def load_all() -> None:
    """
    Load all configured models (best-effort).

    This function is intentionally resilient: if Model A artifacts are missing or invalid,
    Model B should still be able to load (and vice versa). This ensures endpoints like
    `/predict/segmentation` work end-to-end when only Model B artifacts are provided.

    Errors are recorded in `LOAD_ERRORS` for debugging/inspection.
    """
    global MODEL_A, MODEL_B, LOAD_ERRORS

    LOAD_ERRORS = {}

    if settings.chris_model_a_provider.lower() == "onnx":
        try:
            MODEL_A = load_model_a_onnx(
                onnx_path=settings.chris_model_a_path,
                meta_path=settings.chris_model_a_meta_path,
                scaler_x_path=settings.chris_model_a_scaler_x_path,
                scaler_y_path=settings.chris_model_a_scaler_y_path,
            )
        except Exception as e:
            # Model A is optional for Model B endpoints; never block Model B.
            MODEL_A = None
            LOAD_ERRORS["model_a"] = str(e)

    if settings.chris_model_b_provider.lower() == "onnx":
        try:
            MODEL_B = load_model_b_onnx(
                onnx_path=settings.chris_model_b_path,
                meta_path=settings.chris_model_b_meta_path,
            )
        except Exception as e:
            MODEL_B = None
            LOAD_ERRORS["model_b"] = str(e)
