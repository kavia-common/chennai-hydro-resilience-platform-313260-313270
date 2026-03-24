# Model B backend notebooks

This folder contains backend-focused notebooks intended for local validation and reproducible execution of the CHRIS Model B pipeline using the same Python modules that the FastAPI service uses.

## Notebook: `model_b_backend_pipeline.ipynb`

This notebook runs an app-compatible Model B workflow:

1. Loads exported artifacts (ONNX + `meta.json`).
2. Runs terrain segmentation inference (U-Net).
3. Detects sponge zones (connected components over `vacant=1` OR `flooded=5`).
4. Generates pixel-space GeoJSON polygons for sponge zones.
5. Writes outputs (mask JSON, zone metrics JSON, GeoJSON, and optional PNG visualizations).

The notebook uses the backend code directly:

- `app/ml/model_b.py` (`load_model_b_onnx`, `predict_segmentation`, `detect_sponge_zones`, `sponge_zones_to_geojson`)
- It therefore matches the FastAPI endpoints:
  - `POST /predict/segmentation`
  - `POST /predict/terrain_analysis`
  - `POST /predict/sponge_zones_geojson`

## Expected artifact layout

Place exported files here:

```text
chris_backend/
  models/
    model_b/
      unet.onnx
      meta.json
```

The `meta.json` may optionally include `sponge_zones` to override the notebook defaults (pixel resolution, recharge depth, min-zone pixels, max-zone hectares). See `chris_backend/README.md` for the export format used by this repo.

## Input images

The notebook expects an RGB image patch on disk. A convenient default location is:

```text
chris_backend/notebooks/data/sample_patch.png
```

The backend will resize to the model input size (typically 256×256) and normalize using `uint8 / 255.0`, matching the authoritative Colab pipeline.

## GeoJSON output caveat

GeoJSON geometry is expressed in image pixel coordinates because the backend currently does not receive georeferencing metadata with image uploads. Producing WGS84 GeoJSON requires upstream geocoding and raster metadata that is not part of this repository yet.
