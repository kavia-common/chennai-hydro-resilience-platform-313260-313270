from __future__ import annotations

from fastapi import APIRouter, File, Query, UploadFile

from app.core.api_errors import InvalidInputError
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
    summary="Model A: Predict next-month rainfall and binary flood probability",
    description=(
        "Runs Model A (LSTM rainfall forecaster) when available.\n\n"
        "If `CHRIS_MODEL_A_MOCK_MODE=true`, a deterministic mock model is used so the frontend can "
        "work without ONNX/scaler artifacts.\n\n"
        "Flood probability is currently a deterministic 0/100 based on meta.flood_threshold_mm."
    ),
    operation_id="predictFloodRisk",
)
# PUBLIC_INTERFACE
def predict_flood_risk(req: FloodRiskRequest) -> FloodRiskResponse:
    """Run Model A flood-risk inference from a seq_len window of climate indices + month."""
    model_a = registry.get_model_a()

    payload = [s.model_dump() for s in req.sequence]
    try:
        out = predict_next_rainfall_mm(
            model_a,
            payload,
            mock_baseline_mm=float(registry.settings.chris_model_a_mock_baseline_mm)
            if hasattr(registry, "settings")
            else 200.0,
        )
    except ValueError as e:
        # Map deterministic validation errors to a stable 400 response.
        raise InvalidInputError(status_code=400, code="invalid_request", message=str(e), details=None) from e

    return FloodRiskResponse(**out)


@router.post(
    "/segmentation",
    response_model=SegmentationResponse,
    summary="Model B: Terrain segmentation (U-Net)",
    description=(
        "Runs Model B (U-Net) to produce a per-pixel class mask (argmax of softmax).\n\n"
        "Input: image file (PNG/JPG). Backend resizes to 256x256 (or meta.input_size) and normalizes /255."
    ),
    operation_id="predictSegmentation",
)
# PUBLIC_INTERFACE
async def predict_segmentation_api(file: UploadFile = File(...)) -> SegmentationResponse:
    """Run Model B segmentation only (backwards-compatible endpoint)."""
    model_b = registry.get_model_b()
    data = await file.read()
    if not data:
        raise InvalidInputError(status_code=400, code="empty_file", message="Uploaded file is empty.", details=None)

    out = predict_segmentation(model_b, data)
    return SegmentationResponse(**out)


@router.post(
    "/terrain_analysis",
    response_model=TerrainAnalysisResponse,
    summary="Model B: Terrain segmentation + sponge-zone detection",
    description=(
        "Runs Model B segmentation, then applies sponge-zone detection per the authoritative notebook:\n"
        "- recharge candidates = vacant (class 1) + flooded (class 5)\n"
        "- connected components, filter by min_zone_pixels\n"
        "- compute area + storage capacity (depth-based)\n"
        "- priority score boosts flood-coincident zones\n"
        "- filters out unrealistically large zones via max_zone_ha\n\n"
        "Returns segmentation outputs plus zone list and volumetric summary."
    ),
    operation_id="predictTerrainAnalysis",
)
# PUBLIC_INTERFACE
async def predict_terrain_analysis(
    file: UploadFile = File(...),
    include_mask: bool = Query(
        default=True,
        description="If false, the API will still compute zones but return an empty mask to reduce payload size.",
    ),
) -> TerrainAnalysisResponse:
    """Run combined Model B analysis (segmentation + sponge zones)."""
    model_b = registry.get_model_b()
    data = await file.read()
    if not data:
        raise InvalidInputError(status_code=400, code="empty_file", message="Uploaded file is empty.", details=None)

    seg = predict_segmentation(model_b, data)

    # Convert mask back to ndarray for sponge-zone analysis.
    mask_arr = seg["mask"]
    mask_np = __import__("numpy").array(mask_arr, dtype="int32")  # avoid reimport lint churn

    zones_out = detect_sponge_zones(
        mask=mask_np,
        classes=model_b.meta.classes,
        constants=model_b.meta.sponge_constants,
    )

    if not include_mask:
        seg["mask"] = []

    return TerrainAnalysisResponse(
        mask=seg["mask"],
        proportions=seg["proportions"],
        sponge_zones=zones_out["sponge_zones"],
        sponge_summary=zones_out["sponge_summary"],
    )


@router.post(
    "/sponge_zones_geojson",
    response_model=GeoJSONFeatureCollection,
    summary="Model B: Sponge-zone GeoJSON (pixel-coordinate polygons)",
    description=(
        "Runs Model B segmentation + sponge-zone detection and returns a GeoJSON FeatureCollection.\n\n"
        "Important: Output geometry is in image pixel coordinates (not WGS84), because this backend currently "
        "accepts only an image patch without georeferencing."
    ),
    operation_id="predictSpongeZonesGeoJSON",
)
# PUBLIC_INTERFACE
async def predict_sponge_zones_geojson(file: UploadFile = File(...)) -> GeoJSONFeatureCollection:
    """Generate pixel-space GeoJSON bounding-box polygons for detected sponge zones."""
    model_b = registry.get_model_b()
    data = await file.read()
    if not data:
        raise InvalidInputError(status_code=400, code="empty_file", message="Uploaded file is empty.", details=None)

    seg = predict_segmentation(model_b, data)
    mask_np = __import__("numpy").array(seg["mask"], dtype="int32")

    zones_out = detect_sponge_zones(
        mask=mask_np,
        classes=model_b.meta.classes,
        constants=model_b.meta.sponge_constants,
    )

    geojson_dict = sponge_zones_to_geojson(zones_out["sponge_zones"])
    return GeoJSONFeatureCollection.model_validate(geojson_dict)
