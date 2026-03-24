from __future__ import annotations

import json
from dataclasses import dataclass
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
    provider: str
    meta: ModelAMeta
    scaler_x: Any
    scaler_y: Any
    onnx: OnnxModel | None = None


def load_model_a_onnx(
    onnx_path: str,
    meta_path: str,
    scaler_x_path: str,
    scaler_y_path: str,
) -> ModelAArtifacts:
    if joblib is None:
        raise RuntimeError("joblib is required to load scalers; add joblib to requirements if missing.")

    meta_raw = json.load(open(meta_path, "r"))
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


def predict_next_rainfall_mm(art: ModelAArtifacts, sequence: list[dict[str, float]]) -> dict[str, float]:
    if art.provider != "onnx" or art.onnx is None:
        raise RuntimeError("Only ONNX provider is currently wired in this repo.")

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
