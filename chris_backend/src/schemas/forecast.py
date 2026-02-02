"""
Pydantic schemas for flood risk forecast endpoints.

These models define the request/response structure for the temporal
LSTM-based flood prediction API with enhanced validation.
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime


class ForecastRequest(BaseModel):
    """
    Request schema for generating flood risk forecasts.
    
    Attributes:
        years: Number of years to forecast (default: 5, range: 1-10)
        include_climate_factors: Whether to include ONI/IOD anomalies in response
    """
    years: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of years to forecast into the future (1-10)"
    )
    include_climate_factors: bool = Field(
        default=True,
        description="Include climate driver data (ONI, IOD) in response"
    )
    
    @field_validator('years')
    @classmethod
    def validate_years(cls, v):
        """Ensure years is within reasonable bounds."""
        if v < 1:
            raise ValueError('years must be at least 1')
        if v > 10:
            raise ValueError('years cannot exceed 10')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "years": 5,
                "include_climate_factors": True
            }
        }
    )


class CitywideRiskRecord(BaseModel):
    """
    Single year's citywide flood risk prediction.
    
    This matches the 'citywide_risk' Supabase table schema.
    """
    id: Optional[str] = Field(None, description="UUID primary key")
    year: int = Field(
        ...,
        ge=2000,
        le=2100,
        description="Forecast year (2000-2100)"
    )
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
        ge=-3.0,
        le=3.0,
        description="NOAA ONI El Niño index anomaly (-3 to +3)"
    )
    iod_anomaly: Optional[float] = Field(
        None,
        ge=-2.0,
        le=2.0,
        description="Indian Ocean Dipole anomaly (-2 to +2)"
    )
    predicted_rainfall_mm: Optional[float] = Field(
        None,
        ge=0.0,
        le=5000.0,
        description="Predicted annual rainfall in millimeters (0-5000)"
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Model confidence score (0-1)"
    )
    created_at: Optional[datetime] = Field(None, description="Record creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Record last update timestamp")
    
    @field_validator('risk_category')
    @classmethod
    def validate_risk_category(cls, v):
        """Ensure risk category is valid."""
        valid_categories = ['Low', 'Moderate', 'High', 'Critical']
        if v not in valid_categories:
            raise ValueError(f'risk_category must be one of {valid_categories}')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
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
    )


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
    
    model_config = ConfigDict(
        json_schema_extra={
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
                "model_version": "v1.0-lstm-precomputed",
                "generated_at": "2026-02-02T10:30:00Z",
                "message": "Using pre-computed predictions. ML model integration pending."
            }
        }
    )
