from __future__ import annotations

from fastapi import APIRouter

from app.ml import registry
from app.schemas.model_info import ModelInfoResponse

router = APIRouter(prefix="/model", tags=["model"])


@router.get(
    "/info",
    response_model=ModelInfoResponse,
    summary="Model diagnostics: providers, artifact presence, and load status",
    description=(
        "Returns frontend-facing diagnostics for Model A and Model B.\n\n"
        "Includes:\n"
        "- Whether each artifact path exists (onnx/meta/scalers)\n"
        "- Whether each model is currently loaded\n"
        "- Any last load error captured by the registry\n"
        "- Loaded metadata (seq_len/features/threshold, etc.) when available\n\n"
        "This endpoint never fails due to missing artifacts; it reports status instead."
    ),
    operation_id="getModelInfo",
)
# PUBLIC_INTERFACE
def model_info() -> ModelInfoResponse:
    """Get model diagnostics suitable for UI health panels and debugging."""
    diag = registry.get_model_info_diagnostics()
    # Ignore server_time_iso in response model (schema is model_a/model_b); keeping it in dict for future extension is fine.
    return ModelInfoResponse.model_validate({"model_a": diag["model_a"], "model_b": diag["model_b"]})
