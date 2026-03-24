from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.ml import registry
from app.ml.model_a import predict_next_rainfall_mm
from app.ml.model_b import detect_sponge_zones, predict_segmentation, sponge_zones_to_geojson
from app.schemas.predict import (
    FloodRiskRequest,
    FloodRiskResponse,
    GeoJSONFeatureCollection,
    SegmentationResponse,
    TerrainAnalysisResponse,
)

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post(
    "/flood_risk",
    response_model=FloodRiskResponse,
    summary="Model 1: Predict next-month rainfall and binary flood probability",
    description=(
        "Runs Model 1 (LSTM rainfall forecaster). The backend applies month cyclical features, "
        "scales using exported sklearn scalers, runs ONNX inference, then inverse-scales to mm.\n\n"
        "Flood probability is currently a deterministic 0/100 based on meta.flood_threshold_mm."
    ),
    operation_id="predictFloodRisk",
)
def predict_flood_risk(req: FloodRiskRequest) -> FloodRiskResponse:
    """Run Model 1 flood-risk inference from a seq_len window of climate indices + month."""
    try:
        if registry.MODEL_A is None:
            registry.load_all()
        if registry.MODEL_A is None:
            raise RuntimeError("Model A not configured/loaded")

        payload = [s.model_dump() for s in req.sequence]
        out = predict_next_rainfall_mm(registry.MODEL_A, payload)
        return FloodRiskResponse(**out)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/segmentation",
    response_model=SegmentationResponse,
    summary="Model 2: Terrain segmentation (U-Net)",
    description=(
        "Runs Model 2 (U-Net) to produce a per-pixel class mask (argmax of softmax).\n\n"
        "Input: image file (PNG/JPG). Backend resizes to 256x256 (or meta.input_size) and normalizes /255."
    ),
    operation_id="predictSegmentation",
)
async def predict_segmentation_api(file: UploadFile = File(...)) -> SegmentationResponse:
    """Run Model 2 segmentation only (backwards-compatible endpoint)."""
    try:
        if registry.MODEL_B is None:
            registry.load_all()
        if registry.MODEL_B is None:
            raise RuntimeError("Model B not configured/loaded")

        data = await file.read()
        out = predict_segmentation(registry.MODEL_B, data)
        return SegmentationResponse(**out)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/terrain_analysis",
    response_model=TerrainAnalysisResponse,
    summary="Model 2: Terrain segmentation + sponge-zone detection",
    description=(
        "Runs Model 2 segmentation, then applies sponge-zone detection per the authoritative notebook:\n"
        "- recharge candidates = vacant (class 1) + flooded (class 5)\n"
        "- connected components, filter by min_zone_pixels\n"
        "- compute area + storage capacity (depth-based)\n"
        "- priority score boosts flood-coincident zones\n"
        "- filters out unrealistically large zones via max_zone_ha\n\n"
        "Returns segmentation outputs plus zone list and volumetric summary."
    ),
    operation_id="predictTerrainAnalysis",
)
async def predict_terrain_analysis(
    file: UploadFile = File(...),
    include_mask: bool = Query(
        default=True,
        description="If false, the API will still compute zones but return an empty mask to reduce payload size.",
    ),
) -> TerrainAnalysisResponse:
    """Run combined Model 2 analysis (segmentation + sponge zones)."""
    try:
        if registry.MODEL_B is None:
            registry.load_all()
        if registry.MODEL_B is None:
            raise RuntimeError("Model B not configured/loaded")

        data = await file.read()
        seg = predict_segmentation(registry.MODEL_B, data)

        # Convert mask back to ndarray for sponge-zone analysis.
        mask_arr = seg["mask"]
        mask_np = __import__("numpy").array(mask_arr, dtype="int32")  # avoid reimport lint churn

        zones_out = detect_sponge_zones(
            mask=mask_np,
            classes=registry.MODEL_B.meta.classes,
            constants=registry.MODEL_B.meta.sponge_constants,
        )

        if not include_mask:
            seg["mask"] = []

        return TerrainAnalysisResponse(
            mask=seg["mask"],
            proportions=seg["proportions"],
            sponge_zones=zones_out["sponge_zones"],
            sponge_summary=zones_out["sponge_summary"],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/sponge_zones_geojson",
    response_model=GeoJSONFeatureCollection,
    summary="Model 2: Sponge-zone GeoJSON (pixel-coordinate polygons)",
    description=(
        "Runs Model 2 segmentation + sponge-zone detection and returns a GeoJSON FeatureCollection.\n\n"
        "Important: Output geometry is in image pixel coordinates (not WGS84), because this backend currently "
        "accepts only an image patch without georeferencing."
    ),
    operation_id="predictSpongeZonesGeoJSON",
)
async def predict_sponge_zones_geojson(file: UploadFile = File(...)) -> GeoJSONFeatureCollection:
    """Generate pixel-space GeoJSON bounding-box polygons for detected sponge zones."""
    try:
        if registry.MODEL_B is None:
            registry.load_all()
        if registry.MODEL_B is None:
            raise RuntimeError("Model B not configured/loaded")

        data = await file.read()
        seg = predict_segmentation(registry.MODEL_B, data)
        mask_np = __import__("numpy").array(seg["mask"], dtype="int32")

        zones_out = detect_sponge_zones(
            mask=mask_np,
            classes=registry.MODEL_B.meta.classes,
            constants=registry.MODEL_B.meta.sponge_constants,
        )

        geojson_dict = sponge_zones_to_geojson(zones_out["sponge_zones"])
        return GeoJSONFeatureCollection.model_validate(geojson_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
