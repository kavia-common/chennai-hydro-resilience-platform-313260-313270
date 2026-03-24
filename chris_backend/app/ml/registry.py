from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from app.core.api_errors import ModelUnavailableError
from app.core.settings import settings
from app.ml.model_a import ModelAArtifacts, create_mock_model_a, load_model_a_onnx, model_a_meta_as_dict
from app.ml.model_b import ModelBArtifacts, load_model_b_onnx

MODEL_A: ModelAArtifacts | None = None
MODEL_B: ModelBArtifacts | None = None

# Captures load errors without preventing other models from loading.
# Keys: "model_a", "model_b"
LOAD_ERRORS: dict[str, str] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_diag(path: str) -> dict[str, Any]:
    abs_path = os.path.abspath(path)
    exists = os.path.exists(abs_path)
    is_file = os.path.isfile(abs_path)
    size_bytes: int | None = None
    modified_iso: str | None = None

    if is_file:
        st = os.stat(abs_path)
        size_bytes = int(st.st_size)
        modified_iso = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()

    return {
        "path": path,
        "abs_path": abs_path,
        "exists": bool(exists),
        "is_file": bool(is_file),
        "size_bytes": size_bytes,
        "modified_time_iso": modified_iso,
    }


def _capture_load_error(key: str, exc: Exception) -> None:
    # Keep errors lightweight and UI-safe; full tracebacks remain in server logs.
    LOAD_ERRORS[key] = str(exc)


def _clear_load_error(key: str) -> None:
    if key in LOAD_ERRORS:
        del LOAD_ERRORS[key]


def _load_model_a() -> ModelAArtifacts:
    if bool(settings.chris_model_a_mock_mode):
        return create_mock_model_a(
            seq_len=int(settings.chris_model_a_mock_seq_len),
            flood_threshold_mm=float(settings.chris_model_a_mock_flood_threshold_mm),
            baseline_mm=float(settings.chris_model_a_mock_baseline_mm),
        )

    provider = settings.chris_model_a_provider.lower()
    if provider != "onnx":
        raise RuntimeError(f"Unsupported Model A provider '{settings.chris_model_a_provider}'. Only 'onnx' is wired.")

    return load_model_a_onnx(
        onnx_path=settings.chris_model_a_path,
        meta_path=settings.chris_model_a_meta_path,
        scaler_x_path=settings.chris_model_a_scaler_x_path,
        scaler_y_path=settings.chris_model_a_scaler_y_path,
    )


def _load_model_b() -> ModelBArtifacts:
    provider = settings.chris_model_b_provider.lower()
    if provider != "onnx":
        raise RuntimeError(f"Unsupported Model B provider '{settings.chris_model_b_provider}'. Only 'onnx' is wired.")

    return load_model_b_onnx(
        onnx_path=settings.chris_model_b_path,
        meta_path=settings.chris_model_b_meta_path,
    )


# PUBLIC_INTERFACE
def ensure_loaded(*, force: bool = False) -> None:
    """
    Ensure configured models are loaded (best-effort).

    Flow name
    ---------
    EnsureModelsLoadedFlow

    Contract
    --------
    Inputs:
        - force: if true, re-attempt loads even if models already present

    Outputs / Side effects:
        - Populates MODEL_A / MODEL_B globals when successful
        - Updates LOAD_ERRORS with any failures
        - Never raises (resilient best-effort load)

    Notes
    -----
    This is intentionally resilient so that Model B can operate even if Model A artifacts
    are missing (and vice versa).
    """
    global MODEL_A, MODEL_B

    # Model A
    if force or MODEL_A is None:
        try:
            MODEL_A = _load_model_a()
            _clear_load_error("model_a")
        except Exception as e:
            MODEL_A = None
            _capture_load_error("model_a", e)

    # Model B
    if force or MODEL_B is None:
        try:
            MODEL_B = _load_model_b()
            _clear_load_error("model_b")
        except Exception as e:
            MODEL_B = None
            _capture_load_error("model_b", e)


# PUBLIC_INTERFACE
def get_model_a() -> ModelAArtifacts:
    """
    Get Model A artifacts or raise a consistent 503 error.

    Flow name: GetModelAOrRaiseFlow
    """
    ensure_loaded(force=False)
    if MODEL_A is None:
        raise ModelUnavailableError(
            status_code=503,
            code="model_a_unavailable",
            message="Model A is not available (not loaded or artifacts missing).",
            details={"load_error": LOAD_ERRORS.get("model_a")},
        )
    return MODEL_A


# PUBLIC_INTERFACE
def get_model_b() -> ModelBArtifacts:
    """
    Get Model B artifacts or raise a consistent 503 error.

    Flow name: GetModelBOrRaiseFlow
    """
    ensure_loaded(force=False)
    if MODEL_B is None:
        raise ModelUnavailableError(
            status_code=503,
            code="model_b_unavailable",
            message="Model B is not available (not loaded or artifacts missing).",
            details={"load_error": LOAD_ERRORS.get("model_b")},
        )
    return MODEL_B


def _model_a_artifacts_diag() -> dict[str, Any]:
    return {
        "onnx": _file_diag(settings.chris_model_a_path),
        "meta": _file_diag(settings.chris_model_a_meta_path),
        "scaler_x": _file_diag(settings.chris_model_a_scaler_x_path),
        "scaler_y": _file_diag(settings.chris_model_a_scaler_y_path),
    }


def _model_b_artifacts_diag() -> dict[str, Any]:
    return {
        "onnx": _file_diag(settings.chris_model_b_path),
        "meta": _file_diag(settings.chris_model_b_meta_path),
    }


# PUBLIC_INTERFACE
def get_model_info_diagnostics() -> dict[str, Any]:
    """
    Build diagnostics for `/model/info`.

    Contract
    --------
    Output is a dict matching ModelInfoResponse schema:
        - model_a: provider config + mock mode + loaded + load_error + artifact presence + meta (if loaded)
        - model_b: provider config + loaded + load_error + artifact presence + meta (if loaded)

    Side effects:
        - Calls ensure_loaded() to populate load status (best-effort).
    """
    ensure_loaded(force=False)

    model_a_loaded = MODEL_A is not None
    model_b_loaded = MODEL_B is not None

    model_a_meta: dict[str, Any] | None = None
    if model_a_loaded and MODEL_A is not None:
        model_a_meta = model_a_meta_as_dict(MODEL_A.meta)

    model_b_meta: dict[str, Any] | None = None
    if model_b_loaded and MODEL_B is not None:
        # Keep lightweight to avoid depending on internal dataclasses:
        model_b_meta = {
            "input_size": MODEL_B.meta.input_size,
            "classes": MODEL_B.meta.classes,
            "sponge_zone_constants": {
                "pixel_res_m": MODEL_B.meta.sponge_constants.pixel_res_m,
                "avg_depth_m": MODEL_B.meta.sponge_constants.avg_depth_m,
                "min_zone_pixels": MODEL_B.meta.sponge_constants.min_zone_pixels,
                "max_zone_ha": MODEL_B.meta.sponge_constants.max_zone_ha,
            },
        }

    return {
        "model_a": {
            "configured_provider": settings.chris_model_a_provider,
            "active_provider": (MODEL_A.provider if model_a_loaded and MODEL_A is not None else None),
            "mock_mode": bool(settings.chris_model_a_mock_mode),
            "loaded": bool(model_a_loaded),
            "load_error": LOAD_ERRORS.get("model_a"),
            "artifacts": _model_a_artifacts_diag(),
            "meta": model_a_meta,
        },
        "model_b": {
            "configured_provider": settings.chris_model_b_provider,
            "active_provider": (MODEL_B.provider if model_b_loaded and MODEL_B is not None else None),
            "mock_mode": False,
            "loaded": bool(model_b_loaded),
            "load_error": LOAD_ERRORS.get("model_b"),
            "artifacts": _model_b_artifacts_diag(),
            "meta": model_b_meta,
        },
        "server_time_iso": _now_iso(),
    }
