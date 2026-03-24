from __future__ import annotations

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
