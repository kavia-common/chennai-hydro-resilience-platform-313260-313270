# CHRIS Backend (FastAPI)

This backend provides a clean inference contract for CHRIS models and supports loading either:
- TensorFlow SavedModel / Keras `.keras` (optional; not included in default requirements), or
- ONNX (recommended) via `onnxruntime`.

## Run locally

```bash
cd chennai-hydro-resilience-platform-313260-313270/chris_backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open:
- http://localhost:8000/docs

## Environment variables

Create/update `.env`:

```env
# --- CORS (recommended for React integration) ---
# Optional: If CHRIS_CORS_ALLOW_ORIGINS is not set, backend will fall back to REACT_APP_FRONTEND_URL.
REACT_APP_FRONTEND_URL=http://localhost:3000
CHRIS_CORS_ALLOW_ORIGINS=http://localhost:3000,https://your-prod-frontend.example.com
CHRIS_CORS_ALLOW_CREDENTIALS=false

# --- Model A ---
CHRIS_MODEL_A_PROVIDER=onnx
CHRIS_MODEL_A_PATH=models/model_a/rainfall_lstm.onnx
CHRIS_MODEL_A_META_PATH=models/model_a/meta.json
CHRIS_MODEL_A_SCALER_X_PATH=models/model_a/scaler_X.joblib
CHRIS_MODEL_A_SCALER_Y_PATH=models/model_a/scaler_y.joblib

# Optional: deterministic mock mode for Model A (frontend demos/dev without artifacts)
CHRIS_MODEL_A_MOCK_MODE=false
CHRIS_MODEL_A_MOCK_SEQ_LEN=12
CHRIS_MODEL_A_MOCK_FLOOD_THRESHOLD_MM=250.0
CHRIS_MODEL_A_MOCK_BASELINE_MM=200.0

# --- Model B ---
CHRIS_MODEL_B_PROVIDER=onnx
CHRIS_MODEL_B_PATH=models/model_b/unet.onnx
CHRIS_MODEL_B_META_PATH=models/model_b/meta.json
```

## Model diagnostics endpoint

### GET `/model/info`

Returns frontend-facing diagnostics for Model A / Model B:
- artifact presence (paths exist, sizes, modified time)
- load status (loaded or not)
- load error string (if last load attempt failed)
- loaded metadata (seq_len/features/threshold/classes) when available

This endpoint does not fail if artifacts are missing; it reports status.

## Colab export steps (EXACT)

### Model A (LSTM rainfall → flood probability)

Your notebook builds:
- `model` (Keras)
- `scaler_X` and `scaler_y` (sklearn MinMaxScaler)
- config: `SEQ_LEN`, `LAG_MONTHS`, `ALL_FEATURES`, `FLOOD_THRESHOLD`

For CHRIS you must export:
1) the model (SavedModel or ONNX)
2) a `meta.json` containing preprocessing/inference parameters

#### Option 1 — Export TensorFlow SavedModel (recommended if serving with TF)

```python
# After training in Colab:
import json, os, joblib
import tensorflow as tf

EXPORT_DIR = "/content/drive/MyDrive/chris_exports/model_a"
os.makedirs(EXPORT_DIR, exist_ok=True)

# 1) Save Keras model
model.save(os.path.join(EXPORT_DIR, "saved_model"), include_optimizer=False)  # SavedModel directory
# Or: model.save(os.path.join(EXPORT_DIR, "model.keras"))

# 2) Save scalers
joblib.dump(scaler_X, os.path.join(EXPORT_DIR, "scaler_X.joblib"))
joblib.dump(scaler_y, os.path.join(EXPORT_DIR, "scaler_y.joblib"))

# 3) Save metadata
meta = {
  "name": "chris_model_a_lstm",
  "task": "monthly_rainfall_forecast_and_flood_probability",
  "seq_len": int(SEQ_LEN),
  "lag_months": int(LAG_MONTHS),
  "features": ALL_FEATURES,         # must match training
  "target": TARGET,
  "flood_threshold_mm": float(FLOOD_THRESHOLD),
  "forecast_horizon": int(FORECAST_H),
  "notes": "Inputs must be monthly features aligned to month start; model expects scaled features in same order."
}
with open(os.path.join(EXPORT_DIR, "meta.json"), "w") as f:
    json.dump(meta, f, indent=2)

print("Exported to:", EXPORT_DIR)
```

#### Option 2 — Export to ONNX (recommended for deployment portability)

In Colab:

```python
!pip install -q tf2onnx onnx

import tf2onnx
import tensorflow as tf
import os, json, joblib

EXPORT_DIR = "/content/drive/MyDrive/chris_exports/model_a"
os.makedirs(EXPORT_DIR, exist_ok=True)

# Convert Keras model -> ONNX
spec = (tf.TensorSpec((None, SEQ_LEN, len(ALL_FEATURES)), tf.float32, name="X"),)
onnx_path = os.path.join(EXPORT_DIR, "rainfall_lstm.onnx")
model_proto, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=13, output_path=onnx_path)

# Save scalers + meta (same as SavedModel option)
joblib.dump(scaler_X, os.path.join(EXPORT_DIR, "scaler_X.joblib"))
joblib.dump(scaler_y, os.path.join(EXPORT_DIR, "scaler_y.joblib"))
with open(os.path.join(EXPORT_DIR, "meta.json"), "w") as f:
    json.dump({
      "name": "chris_model_a_lstm",
      "seq_len": int(SEQ_LEN),
      "lag_months": int(LAG_MONTHS),
      "features": ALL_FEATURES,
      "flood_threshold_mm": float(FLOOD_THRESHOLD),
      "onnx": {"input_name": "X", "output_name": "output"}
    }, f, indent=2)

print("ONNX exported:", onnx_path)
```

**Important**: ONNX export does NOT include sklearn scalers—keep `scaler_X.joblib` and `scaler_y.joblib`.

### Model B (U-Net segmentation)

Export the trained model and a `meta.json` describing:
- class mapping (0..5)
- expected input normalization (uint8 / 255.0)
- output is per-pixel softmax; postprocess via argmax

#### Option 1 — Keras `.keras`

```python
import os, json
EXPORT_DIR = "/content/drive/MyDrive/chris_exports/model_b"
os.makedirs(EXPORT_DIR, exist_ok=True)

model.save(os.path.join(EXPORT_DIR, "unet.keras"), include_optimizer=False)

meta = {
  "name": "chris_model_b_unet",
  "task": "segmentation",
  "input": {"shape": [256,256,3], "dtype": "float32", "normalization": "uint8_to_float32_div_255"},
  "classes": {
    "0": "background",
    "1": "vacant",
    "2": "vegetation",
    "3": "water",
    "4": "built_up",
    "5": "flooded"
  }
}
with open(os.path.join(EXPORT_DIR, "meta.json"), "w") as f:
    json.dump(meta, f, indent=2)
```

#### Option 2 — ONNX

```python
!pip install -q tf2onnx onnx
import tf2onnx, tensorflow as tf, os, json

EXPORT_DIR = "/content/drive/MyDrive/chris_exports/model_b"
os.makedirs(EXPORT_DIR, exist_ok=True)

spec = (tf.TensorSpec((None, 256, 256, 3), tf.float32, name="image"),)
onnx_path = os.path.join(EXPORT_DIR, "unet.onnx")
tf2onnx.convert.from_keras(model, input_signature=spec, opset=13, output_path=onnx_path)

with open(os.path.join(EXPORT_DIR, "meta.json"), "w") as f:
    json.dump({"name":"chris_model_b_unet","onnx":{"input_name":"image"}}, f, indent=2)
```

## Inference contract (what CHRIS backend expects)

### POST `/predict/flood_risk`

Body:
```json
{
  "sequence": [
    {"ONI": 0.1, "DMI": -0.2, "Nino34_ERSST": 0.3, "BEST_ENSO": 0.0, "month": 11},
    ...
  ]
}
```

Length must equal `seq_len` in `meta.json` (or the mock `CHRIS_MODEL_A_MOCK_SEQ_LEN` when mock mode is enabled). Backend will compute `month_sin/cos`, scale via exported scalers, run model, and return:
- `predicted_rainfall_mm`
- `flood_probability_pct` (probability that predicted rainfall exceeds threshold)

### POST `/predict/segmentation`

Accepts `multipart/form-data` with an image file (RGB PNG/JPG) sized 256x256 for now and returns:
- predicted class mask as a 2D array (argmax of per-pixel softmax)
- per-class pixel proportions

### POST `/predict/terrain_analysis`

Accepts `multipart/form-data` with an image file and returns **Model 2 full pipeline**:
- segmentation `mask`
- `proportions`
- `sponge_zones`: connected-component “recharge” zones where (vacant=1) OR (flooded=5)
- `sponge_summary`: total area + estimated capacity using conservative depth estimate

This matches the authoritative notebook logic:
- `pixel_res_m = 10`
- `avg_depth_m = 0.5`
- `min_zone_pixels = 50`
- `max_zone_ha = 50`

### POST `/predict/sponge_zones_geojson`

Returns a GeoJSON `FeatureCollection` where each zone is represented as a **pixel-coordinate** bounding-box polygon.
(Georeferenced GeoJSON requires upstream geocoding/raster metadata; not part of this repo yet.)

## Optional meta.json for sponge zone constants

You may include a `sponge_zones` object in `models/model_b/meta.json` to override defaults:

```json
{
  "sponge_zones": {
    "pixel_res_m": 10.0,
    "avg_depth_m": 0.5,
    "min_zone_pixels": 50,
    "max_zone_ha": 50.0
  }
}
```
