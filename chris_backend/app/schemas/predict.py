from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class FloodRiskStep(BaseModel):
    ONI: float
    DMI: float
    Nino34_ERSST: float
    BEST_ENSO: float
    month: int = Field(ge=1, le=12)


class FloodRiskRequest(BaseModel):
    sequence: list[FloodRiskStep]


class FloodRiskResponse(BaseModel):
    predicted_rainfall_mm: float
    flood_probability_pct: float


class SegmentationResponse(BaseModel):
    mask: list[list[int]]
    proportions: dict[str, float]


class SpongeZone(BaseModel):
    zone_id: int = Field(..., description="Sequential ID of the detected zone in this analysis run.")
    pixel_count: int = Field(..., ge=1, description="Number of pixels in the connected component.")
    area_m2: float = Field(..., ge=0, description="Zone area in square meters.")
    area_ha: float = Field(..., ge=0, description="Zone area in hectares.")
    area_km2: float = Field(..., ge=0, description="Zone area in square kilometers.")
    volume_m3: float = Field(..., ge=0, description="Estimated storage volume in cubic meters.")
    volume_mcm: float = Field(..., ge=0, description="Estimated storage volume in million cubic meters (MCM).")
    centroid_x: float = Field(..., description="Zone centroid X (pixel column coordinate).")
    centroid_y: float = Field(..., description="Zone centroid Y (pixel row coordinate).")
    has_flood: bool = Field(..., description="True if flooded-class pixels are present in this zone.")
    dominant_class: str = Field(..., description="Dominant class name/id inside the zone.")
    priority_score: float = Field(..., ge=0, description="Priority score per notebook: area_ha * (2 if has_flood else 1).")
    bbox: list[int] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Bounding box in pixel coordinates: [x_min, y_min, x_max, y_max].",
    )


class SpongeZoneSummary(BaseModel):
    total_zones_detected: int = Field(..., ge=0)
    total_area_ha: float = Field(..., ge=0)
    total_area_km2: float = Field(..., ge=0)
    total_capacity_mcm: float = Field(..., ge=0)
    flood_coincident_zones: int = Field(..., ge=0)

    # Constants used (echoed to clients for transparency)
    pixel_res_m: float = Field(..., gt=0)
    avg_depth_m: float = Field(..., gt=0)
    min_zone_pixels: int = Field(..., ge=1)
    max_zone_ha: float = Field(..., gt=0)


class TerrainAnalysisResponse(BaseModel):
    """
    Combined Model 2 response:
    - segmentation mask + per-class proportions
    - sponge zones derived from predicted mask
    - volumetric summary
    """

    mask: list[list[int]]
    proportions: dict[str, float]
    sponge_zones: list[SpongeZone]
    sponge_summary: SpongeZoneSummary


class GeoJSONGeometry(BaseModel):
    type: Literal["Polygon"]
    coordinates: list[list[list[float]]]


class GeoJSONFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: int
    geometry: GeoJSONGeometry
    properties: dict[str, Any]


class GeoJSONCRS(BaseModel):
    type: Literal["name"] = "name"
    properties: dict[str, str]


class GeoJSONFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    crs: GeoJSONCRS
    features: list[GeoJSONFeature]
