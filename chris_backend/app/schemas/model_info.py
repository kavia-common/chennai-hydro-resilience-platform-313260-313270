from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FileDiagnostic(BaseModel):
    """Diagnostics about a configured artifact path."""

    path: str = Field(..., description="Configured path (as provided by settings).")
    abs_path: str = Field(..., description="Absolute resolved path on the server.")
    exists: bool = Field(..., description="Whether the path exists.")
    is_file: bool = Field(..., description="Whether the path exists and is a file.")
    size_bytes: int | None = Field(None, description="File size in bytes, if file exists.")
    modified_time_iso: str | None = Field(None, description="Last modified time (ISO8601), if file exists.")


class ModelLoadDiagnostic(BaseModel):
    """Load-time and runtime diagnostics for a model integration."""

    configured_provider: str = Field(..., description="Configured provider from env (e.g., onnx).")
    active_provider: str | None = Field(None, description="Currently active provider (e.g., onnx, mock) if loaded.")
    mock_mode: bool = Field(..., description="Whether mock mode is enabled for this model.")
    loaded: bool = Field(..., description="Whether the model is currently loaded in-process.")
    load_error: str | None = Field(None, description="Load error string if last load attempt failed.")
    artifacts: dict[str, FileDiagnostic] = Field(
        default_factory=dict,
        description="Artifact diagnostics keyed by artifact name (e.g., onnx, meta, scaler_x).",
    )
    meta: dict[str, Any] | None = Field(None, description="Loaded model metadata (if loaded).")


class ModelInfoResponse(BaseModel):
    """Response schema for `/model/info` diagnostics."""

    model_a: ModelLoadDiagnostic
    model_b: ModelLoadDiagnostic
