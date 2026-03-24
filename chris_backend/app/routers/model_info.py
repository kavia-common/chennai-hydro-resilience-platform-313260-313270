from fastapi import APIRouter

from app.ml import registry

router = APIRouter(prefix="/model", tags=["model"])


@router.get("/info")
def model_info() -> dict:
    # Lazy load (safe for server start even without model files)
    if registry.MODEL_A is None or registry.MODEL_B is None:
        try:
            registry.load_all()
        except Exception:
            # allow info even if models missing
            pass

    info: dict = {"model_a": None, "model_b": None}

    if registry.MODEL_A is not None:
        info["model_a"] = {
            "provider": registry.MODEL_A.provider,
            "seq_len": registry.MODEL_A.meta.seq_len,
            "lag_months": registry.MODEL_A.meta.lag_months,
            "features": registry.MODEL_A.meta.features,
            "flood_threshold_mm": registry.MODEL_A.meta.flood_threshold_mm,
        }

    if registry.MODEL_B is not None:
        info["model_b"] = {
            "provider": registry.MODEL_B.provider,
            "input_size": registry.MODEL_B.meta.input_size,
            "classes": registry.MODEL_B.meta.classes,
        }

    return info
