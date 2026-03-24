from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import Image

from app.ml.onnx_runtime import OnnxModel, load_onnx_model, run_onnx

try:
    # Used for connected-component analysis exactly as in the notebook.
    from scipy import ndimage  # type: ignore
except Exception:  # pragma: no cover
    ndimage = None  # type: ignore


@dataclass
class SpongeZoneConstants:
    """
    Constants used for sponge-zone detection and volumetric parameterization.

    These default values are sourced from the provided Model 2 notebook.
    """

    pixel_res_m: float = 10.0  # Sentinel-2 10m resolution
    avg_depth_m: float = 0.5  # conservative recharge depth estimate
    min_zone_pixels: int = 50  # minimum connected vacant/flood pixels
    max_zone_ha: float = 50.0  # cap to realistic max urban vacant land zone


@dataclass
class ModelBMeta:
    input_size: int = 256
    classes: dict[str, str] | None = None
    sponge_constants: SpongeZoneConstants = field(default_factory=SpongeZoneConstants)


@dataclass
class ModelBArtifacts:
    provider: str
    meta: ModelBMeta
    onnx: OnnxModel | None = None


# PUBLIC_INTERFACE
def load_model_b_onnx(onnx_path: str, meta_path: str | None = None) -> ModelBArtifacts:
    """
    Load Model B (U-Net segmentation) artifacts from ONNX.

    Parameters
    ----------
    onnx_path:
        Path to the exported ONNX file.
    meta_path:
        Optional path to `meta.json`. If omitted or missing, sensible defaults are used:
        - input.shape defaults to [256, 256, 3]
        - classes mapping defaults to None
        - sponge_zones constants default to SpongeZoneConstants()

    Returns
    -------
    ModelBArtifacts
        Loaded ONNX runtime session + metadata used by the backend.
    """
    # meta.json is optional to support "drop only an ONNX file" flows.
    meta_raw: dict[str, Any] = {}
    if meta_path:
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta_raw = json.load(f)
        except FileNotFoundError:
            meta_raw = {}

    input_shape = (meta_raw.get("input") or {}).get("shape", [256, 256, 3])
    sponge_raw = meta_raw.get("sponge_zones") or {}

    meta = ModelBMeta(
        input_size=int(input_shape[0]),
        classes=meta_raw.get("classes"),
        sponge_constants=SpongeZoneConstants(
            pixel_res_m=float(sponge_raw.get("pixel_res_m", 10.0)),
            avg_depth_m=float(sponge_raw.get("avg_depth_m", 0.5)),
            min_zone_pixels=int(sponge_raw.get("min_zone_pixels", 50)),
            max_zone_ha=float(sponge_raw.get("max_zone_ha", 50.0)),
        ),
    )
    onnx_model = load_onnx_model(onnx_path)
    return ModelBArtifacts(provider="onnx", meta=meta, onnx=onnx_model)


def _preprocess_image_rgb(image_bytes: bytes, size: int) -> np.ndarray:
    """
    Preprocess an RGB image for the U-Net model.

    Notebook reference: uint8 image / 255.0 normalization.
    Returns NCHW? The ONNX exported from TF is typically NHWC; we keep NHWC.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((size, size))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return arr[np.newaxis, :, :, :]  # (1,H,W,3)


def _mask_proportions(mask: np.ndarray) -> dict[str, float]:
    unique, counts = np.unique(mask, return_counts=True)
    total = float(mask.size)
    return {str(int(k)): float(v) / total for k, v in zip(unique, counts, strict=False)}


def _dominant_class_name(mask: np.ndarray, classes: dict[str, str] | None) -> str:
    dominant = int(np.bincount(mask.astype(np.int64).ravel()).argmax())
    if classes is None:
        return str(dominant)
    return classes.get(str(dominant), str(dominant))


# PUBLIC_INTERFACE
def predict_segmentation(art: ModelBArtifacts, image_bytes: bytes) -> dict[str, Any]:
    """
    Run Model 2 segmentation (U-Net) on an input image.

    Parameters
    ----------
    art:
        Loaded Model B artifacts.
    image_bytes:
        Raw RGB image bytes. The backend will resize to meta.input_size and normalize /255.

    Returns
    -------
    dict
        - mask: 2D list[int] of class IDs (argmax of per-pixel softmax)
        - proportions: per-class fraction of pixels (0..1)
    """
    if art.provider != "onnx" or art.onnx is None:
        raise RuntimeError("Only ONNX provider is currently wired in this repo.")

    x = _preprocess_image_rgb(image_bytes, art.meta.input_size).astype(np.float32)
    outputs = run_onnx(art.onnx, x)

    # Common exports:
    # - TF/Keras -> ONNX often yields (1,H,W,C) (NHWC)
    # - Some pipelines yield (1,C,H,W) (NCHW)
    y = np.asarray(list(outputs.values())[0])

    if y.ndim != 4 or y.shape[0] != 1:
        raise RuntimeError(f"Unexpected Model B ONNX output shape: {tuple(y.shape)}")

    # Heuristic: "channels" dimension is typically a small number (e.g., 6 classes).
    # Prefer NHWC if the last dim looks like channels; otherwise handle NCHW.
    if y.shape[-1] <= 64:
        # (1,H,W,C)
        mask = np.argmax(y, axis=-1)[0].astype(np.int32)  # (H,W)
    elif y.shape[1] <= 64:
        # (1,C,H,W)
        mask = np.argmax(y, axis=1)[0].astype(np.int32)  # (H,W)
    else:
        raise RuntimeError(f"Could not infer channel axis for Model B ONNX output shape: {tuple(y.shape)}")

    return {"mask": mask.tolist(), "proportions": _mask_proportions(mask)}


# PUBLIC_INTERFACE
def detect_sponge_zones(
    *,
    mask: np.ndarray,
    classes: dict[str, str] | None = None,
    constants: SpongeZoneConstants | None = None,
) -> dict[str, Any]:
    """
    Detect sponge zones from a predicted segmentation mask, per Model 2 notebook.

    Notebook logic (authoritative):
    - recharge candidates = vacant land (class 1) + flooded area (class 5)
    - connected component analysis
    - filter components smaller than MIN_ZONE_PIXELS
    - compute area + volumetric capacity with conservative AVG_DEPTH_M
    - priority_score = area_ha * (2 if has_flood else 1)
    - filter zones > MAX_ZONE_HA (realism cap)
    - return zones sorted by priority_score desc

    Parameters
    ----------
    mask:
        2D integer array (H,W) of class IDs.
    classes:
        Optional mapping "0".."5" -> class name.
    constants:
        Sponge-zone detection constants. If omitted, notebook defaults are used.

    Returns
    -------
    dict
        - sponge_zones: list[dict] with zone metrics and bbox in pixel coordinates
        - sponge_summary: dict summary totals
    """
    if ndimage is None:
        raise RuntimeError("scipy is required for sponge-zone detection (scipy.ndimage).")

    c = constants or SpongeZoneConstants()

    pixel_area_m2 = float(c.pixel_res_m) ** 2
    pixel_area_km2 = pixel_area_m2 / 1e6

    # Recharge candidates = vacant (1) + flooded (5)
    recharge_mask = ((mask == 1) | (mask == 5)).astype(np.uint8)

    labeled, n_components = ndimage.label(recharge_mask)

    sponge_zones: list[dict[str, Any]] = []
    zone_id = 0

    for comp_id in range(1, int(n_components) + 1):
        component = labeled == comp_id
        pixel_count = int(component.sum())

        if pixel_count < int(c.min_zone_pixels):
            continue

        area_m2 = pixel_count * pixel_area_m2
        area_km2 = area_m2 / 1e6
        area_ha = area_m2 / 10000.0

        # Volumetric capacity
        volume_m3 = area_m2 * float(c.avg_depth_m)
        volume_mcm = volume_m3 / 1e6  # Million Cubic Meters

        # Zone centroid in pixel coordinates (x=col, y=row)
        cy, cx = ndimage.center_of_mass(component)

        # Has flood?
        has_flood = bool((mask[component] == 5).any())

        # Priority score: larger + flooded = higher priority
        priority_score = float(area_ha) * (2.0 if has_flood else 1.0)

        # Dominant class (name)
        dominant_cls_id = int(np.bincount(mask[component].astype(np.int64)).argmax())
        dominant_class = (classes or {}).get(str(dominant_cls_id), str(dominant_cls_id))

        # Bounding box (pixel coords)
        ys, xs = np.where(component)
        x_min, x_max = int(xs.min()), int(xs.max())
        y_min, y_max = int(ys.min()), int(ys.max())

        sponge_zones.append(
            {
                "zone_id": zone_id,
                "pixel_count": pixel_count,
                "area_m2": round(area_m2, 1),
                "area_ha": round(area_ha, 3),
                "area_km2": round(area_km2, 6),
                "volume_m3": round(volume_m3, 1),
                "volume_mcm": round(volume_mcm, 8),
                "centroid_x": round(float(cx), 2),
                "centroid_y": round(float(cy), 2),
                "has_flood": has_flood,
                "dominant_class": dominant_class,
                "priority_score": round(priority_score, 4),
                "bbox": [x_min, y_min, x_max, y_max],
            }
        )
        zone_id += 1

    # Sort by priority and apply realism cap (as in notebook step 4 filter).
    sponge_zones = sorted(sponge_zones, key=lambda z: float(z["priority_score"]), reverse=True)
    sponge_zones = [z for z in sponge_zones if float(z["area_ha"]) <= float(c.max_zone_ha)]

    total_area_ha = float(sum(float(z["area_ha"]) for z in sponge_zones))
    total_area_km2 = float(sum(float(z["area_km2"]) for z in sponge_zones))
    total_capacity_mcm = float(sum(float(z["volume_mcm"]) for z in sponge_zones))
    flood_coincident = int(sum(1 for z in sponge_zones if bool(z["has_flood"])))

    summary = {
        "total_zones_detected": int(len(sponge_zones)),
        "total_area_ha": round(total_area_ha, 3),
        "total_area_km2": round(total_area_km2, 6),
        "total_capacity_mcm": round(total_capacity_mcm, 8),
        "flood_coincident_zones": int(flood_coincident),
        "pixel_res_m": float(c.pixel_res_m),
        "avg_depth_m": float(c.avg_depth_m),
        "min_zone_pixels": int(c.min_zone_pixels),
        "max_zone_ha": float(c.max_zone_ha),
    }

    return {"sponge_zones": sponge_zones, "sponge_summary": summary}


# PUBLIC_INTERFACE
def sponge_zones_to_geojson(sponge_zones: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Convert sponge zones into a GeoJSON FeatureCollection in pixel-coordinate space.

    Note:
    - Because inference inputs are 256x256 patches without georeferencing in this backend,
      the geometry is expressed in image pixel coordinates.
    - Geometry is a bounding-box polygon around each connected component.

    Returns
    -------
    dict
        GeoJSON FeatureCollection.
    """
    features: list[dict[str, Any]] = []
    for z in sponge_zones:
        x_min, y_min, x_max, y_max = z["bbox"]
        poly = [
            [x_min, y_min],
            [x_max, y_min],
            [x_max, y_max],
            [x_min, y_max],
            [x_min, y_min],
        ]
        features.append(
            {
                "type": "Feature",
                "id": z["zone_id"],
                "geometry": {"type": "Polygon", "coordinates": [poly]},
                "properties": {k: v for k, v in z.items() if k != "bbox"},
            }
        )

    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "image-pixels"}},
        "features": features,
    }
