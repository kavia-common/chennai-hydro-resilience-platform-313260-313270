from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from app.ml.onnx_runtime import OnnxModel, load_onnx_model, run_onnx

try:
    import joblib  # type: ignore
except Exception:  # pragma: no cover
    joblib = None  # type: ignore


@dataclass
class ModelAMeta:
    seq_len: int
    lag_months: int
    features: list[str]
    flood_threshold_mm: float
    onnx_input_name: str | None = None


@dataclass
class ModelAArtifacts:
    provider: str  # "onnx" | "mock"
    meta: ModelAMeta
    scaler_x: Any
    scaler_y: Any
    onnx: OnnxModel | None = None


# PUBLIC_INTERFACE
def load_model_a_onnx(
    onnx_path: str,
    meta_path: str,
    scaler_x_path: str,
    scaler_y_path: str,
) -> ModelAArtifacts:
    """
    Load Model A ONNX + preprocessing artifacts.

    Contract
    --------
    Inputs:
        - onnx_path: ONNX file path
        - meta_path: meta.json containing seq_len, features, flood_threshold_mm, optional onnx input_name
        - scaler_x_path: joblib scaler for X
        - scaler_y_path: joblib scaler for y

    Output:
        - ModelAArtifacts(provider="onnx", ...)

    Errors:
        - RuntimeError if joblib missing
        - FileNotFoundError/JSON errors if artifacts invalid
        - onnxruntime exceptions for invalid ONNX
    """
    if joblib is None:
        raise RuntimeError("joblib is required to load scalers; add joblib to requirements if missing.")

    meta_raw = json.load(open(meta_path, "r", encoding="utf-8"))
    meta = ModelAMeta(
        seq_len=int(meta_raw["seq_len"]),
        lag_months=int(meta_raw.get("lag_months", 0)),
        features=list(meta_raw["features"]),
        flood_threshold_mm=float(meta_raw["flood_threshold_mm"]),
        onnx_input_name=(meta_raw.get("onnx") or {}).get("input_name"),
    )

    scaler_x = joblib.load(scaler_x_path)
    scaler_y = joblib.load(scaler_y_path)

    onnx_model = load_onnx_model(onnx_path)
    return ModelAArtifacts(provider="onnx", meta=meta, scaler_x=scaler_x, scaler_y=scaler_y, onnx=onnx_model)


# PUBLIC_INTERFACE
def create_mock_model_a(*, seq_len: int, flood_threshold_mm: float, baseline_mm: float = 200.0) -> ModelAArtifacts:
    """
    Create deterministic, env-controlled mock Model A artifacts.

    Purpose
    -------
    - Allows frontend development and demos without requiring ONNX/scaler files.
    - Behavior is deterministic (no randomness) for debuggable UI behavior.

    Contract
    --------
    Inputs:
        - seq_len: required input sequence length
        - flood_threshold_mm: threshold used for 0/100 flood probability
        - baseline_mm: baseline rainfall magnitude (mm)

    Output:
        - ModelAArtifacts(provider="mock") with meta describing accepted features.

    Errors:
        - None (pure construction).
    """
    meta = ModelAMeta(
        seq_len=int(seq_len),
        lag_months=0,
        features=["ONI", "DMI", "Nino34_ERSST", "BEST_ENSO", "month_sin", "month_cos"],
        flood_threshold_mm=float(flood_threshold_mm),
        onnx_input_name=None,
    )
    # Keep scaler_x/scaler_y as None for mock provider (not used).
    return ModelAArtifacts(provider="mock", meta=meta, scaler_x=None, scaler_y=None, onnx=None)


def month_to_cyc(month: int) -> tuple[float, float]:
    m = float(month)
    return float(np.sin(2 * np.pi * m / 12.0)), float(np.cos(2 * np.pi * m / 12.0))


def build_feature_matrix(sequence: list[dict[str, float]], feature_names: list[str]) -> np.ndarray:
    """
    sequence: list of timesteps, each dict has climate indexes + 'month' (1..12)
    feature_names: includes climate cols + 'month_sin' + 'month_cos'
    """
    rows: list[list[float]] = []
    for step in sequence:
        month = int(step.get("month", 1))
        month_sin, month_cos = month_to_cyc(month)
        row: list[float] = []
        for f in feature_names:
            if f == "month_sin":
                row.append(month_sin)
            elif f == "month_cos":
                row.append(month_cos)
            else:
                row.append(float(step[f]))
        rows.append(row)
    return np.asarray(rows, dtype=np.float32)


def _predict_next_rainfall_mm_mock(art: ModelAArtifacts, sequence: list[dict[str, float]], baseline_mm: float) -> dict[str, float]:
    """
    Deterministic mock predictor.

    Rationale
    ---------
    We produce plausible-looking values based on:
    - mean of ENSO-related indices across the window
    - a seasonal (monsoon) sinusoid peaking around October (month 10)
    """
    if len(sequence) != art.meta.seq_len:
        raise ValueError(f"sequence length must be {art.meta.seq_len}, got {len(sequence)}")

    def _mean(key: str) -> float:
        vals = [float(s.get(key, 0.0)) for s in sequence]
        return float(sum(vals) / max(1, len(vals)))

    oni = _mean("ONI")
    dmi = _mean("DMI")
    nino = _mean("Nino34_ERSST")
    best = _mean("BEST_ENSO")

    month = int(sequence[-1].get("month", 1))
    # Seasonal factor: peak rainfall around month 10 (Oct) in Chennai monsoon context.
    seasonal = float(np.cos(2 * np.pi * (float(month) - 10.0) / 12.0))

    # Weighted linear combination (deterministic).
    rainfall_mm = (
        float(baseline_mm)
        + 60.0 * seasonal
        + 35.0 * oni
        - 20.0 * dmi
        + 25.0 * nino
        + 10.0 * best
    )
    rainfall_mm = float(max(0.0, rainfall_mm))
    flood_prob_pct = 100.0 if rainfall_mm > float(art.meta.flood_threshold_mm) else 0.0
    return {"predicted_rainfall_mm": float(rainfall_mm), "flood_probability_pct": float(flood_prob_pct)}


# PUBLIC_INTERFACE
def predict_next_rainfall_mm(art: ModelAArtifacts, sequence: list[dict[str, float]], *, mock_baseline_mm: float = 200.0) -> dict[str, float]:
    """
    Predict next-month rainfall in mm and flood probability %.

    Contract
    --------
    Inputs:
        - art: ModelAArtifacts produced by either load_model_a_onnx() or create_mock_model_a()
        - sequence: list[dict] of length art.meta.seq_len; each dict includes climate indices and month (1..12)
        - mock_baseline_mm: baseline used only if art.provider == "mock"

    Output:
        - dict with keys:
            - predicted_rainfall_mm: float >= 0
            - flood_probability_pct: float in {0, 100} (current deterministic thresholding)

    Errors:
        - ValueError for invalid sequence length
        - RuntimeError for unsupported providers or missing ONNX session
    """
    if art.provider == "mock":
        return _predict_next_rainfall_mm_mock(art, sequence, baseline_mm=float(mock_baseline_mm))

    if art.provider != "onnx" or art.onnx is None:
        raise RuntimeError("Only ONNX and mock providers are supported in this repo.")

    if len(sequence) != art.meta.seq_len:
        raise ValueError(f"sequence length must be {art.meta.seq_len}, got {len(sequence)}")

    # Build X (seq_len, n_features) then scale per-feature
    x = build_feature_matrix(sequence, art.meta.features)
    x_scaled = art.scaler_x.transform(x)

    # Add batch dim -> (1, seq_len, n_features)
    x_in = x_scaled[np.newaxis, :, :].astype(np.float32)

    outputs = run_onnx(art.onnx, x_in)

    # take first output tensor
    y_scaled = list(outputs.values())[0]
    y_scaled = np.asarray(y_scaled).reshape(1, -1)
    y_mm = art.scaler_y.inverse_transform(y_scaled)[0, 0]
    y_mm = float(max(0.0, y_mm))

    flood_prob_pct = 100.0 if y_mm > art.meta.flood_threshold_mm else 0.0
    return {"predicted_rainfall_mm": y_mm, "flood_probability_pct": float(flood_prob_pct)}


# PUBLIC_INTERFACE
def model_a_meta_as_dict(meta: ModelAMeta) -> dict[str, Any]:
    """Serialize Model A metadata for diagnostics output."""
    return asdict(meta)
