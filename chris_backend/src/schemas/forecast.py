"""
Pydantic schemas for flood risk forecast endpoints.

These models define the request/response structure for the temporal
LSTM-based flood prediction API.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ForecastRequest(BaseModel):
    """
    Request schema for generating flood risk forecasts.
    
    Attributes:
        years: Number of years to forecast (default: 5, max: 10)
        include_climate_factors: Whether to include ONI/IOD anomalies in response
    """
    years: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of years to forecast into the future"
    )
    include_climate_factors: bool = Field(
        default=True,
        description="Include climate driver data (ONI, IOD) in response"
    )


class CitywideRiskRecord(BaseModel):
    """
    Single year's citywide flood risk prediction.
    
    This matches the 'citywide_risk' Supabase table schema.
    """
    id: Optional[str] = Field(None, description="UUID primary key")
    year: int = Field(..., description="Forecast year")
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Computed risk score (0-100)"
    )
    risk_category: str = Field(
        ...,
        description="Risk classification: Low, Moderate, High, Critical"
    )
    oni_anomaly: Optional[float] = Field(
        None,
        description="NOAA ONI El Niño index anomaly"
    )
    iod_anomaly: Optional[float] = Field(
        None,
        description="Indian Ocean Dipole anomaly"
    )
    predicted_rainfall_mm: Optional[float] = Field(
        None,
        description="Predicted annual rainfall in millimeters"
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Model confidence score (0-1)"
    )
    created_at: Optional[datetime] = Field(None, description="Record creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Record last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "year": 2027,
                "risk_score": 88.7,
                "risk_category": "Critical",
                "oni_anomaly": 1.8,
                "iod_anomaly": 0.65,
                "predicted_rainfall_mm": 1650.8,
                "confidence": 0.87
            }
        }


class ForecastResponse(BaseModel):
    """
    Response schema for forecast endpoint.
    
    Contains list of yearly predictions and metadata.
    """
    success: bool = Field(..., description="Whether the forecast was successful")
    data: List[CitywideRiskRecord] = Field(
        ...,
        description="List of yearly risk predictions"
    )
    model_version: Optional[str] = Field(
        None,
        description="Version of the LSTM model used (e.g., 'v1.0-lstm-100epoch')"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when forecast was generated"
    )
    message: Optional[str] = Field(
        None,
        description="Additional information or warnings"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [
                    {
                        "year": 2025,
                        "risk_score": 65.5,
                        "risk_category": "Moderate",
                        "predicted_rainfall_mm": 1250.5,
                        "confidence": 0.82
                    }
                ],
                "model_version": "v1.0-lstm-placeholder",
                "generated_at": "2026-02-02T10:30:00Z",
                "message": "Using pre-computed predictions. ML model integration pending."
            }
        }
