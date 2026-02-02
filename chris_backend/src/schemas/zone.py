"""
Pydantic schemas for sponge zone mapping endpoints.

These models define the GeoJSON-compliant structure for spatial
U-Net-based sponge zone data with enhanced validation.
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any


class ZoneProperties(BaseModel):
    """
    Properties for a single sponge zone (GeoJSON Feature properties).
    """
    zone_id: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Zone identifier (e.g., 'Z001')"
    )
    zone_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable zone name"
    )
    capacity_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Water storage capacity score (0-100)"
    )
    capacity_category: str = Field(
        ...,
        description="Capacity classification: Low, Moderate, High"
    )
    vv_amplitude: Optional[float] = Field(
        None,
        ge=-30.0,
        le=0.0,
        description="Sentinel-1 VV polarization amplitude (dB, typically -30 to 0)"
    )
    vh_backscatter: Optional[float] = Field(
        None,
        ge=-30.0,
        le=0.0,
        description="Sentinel-1 VH backscatter coefficient (dB, typically -30 to 0)"
    )
    mndwi: Optional[float] = Field(
        None,
        ge=-1.0,
        le=1.0,
        description="Modified Normalized Difference Water Index (-1 to 1)"
    )
    ndvi: Optional[float] = Field(
        None,
        ge=-1.0,
        le=1.0,
        description="Normalized Difference Vegetation Index (-1 to 1)"
    )
    terrain_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Terrain classification (e.g., 'Wetland', 'Marsh')"
    )
    recommendation: Optional[str] = Field(
        None,
        max_length=500,
        description="Action recommendation for city planners"
    )
    
    @field_validator('capacity_category')
    @classmethod
    def validate_capacity_category(cls, v):
        """Ensure capacity category is valid."""
        valid_categories = ['Low', 'Moderate', 'High']
        if v not in valid_categories:
            raise ValueError(f'capacity_category must be one of {valid_categories}')
        return v
    
    @field_validator('zone_id')
    @classmethod
    def validate_zone_id(cls, v):
        """Sanitize zone_id to prevent injection."""
        # Only allow alphanumeric and underscore/dash
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('zone_id must contain only alphanumeric characters, underscores, and dashes')
        return v


class SpongeZoneFeature(BaseModel):
    """
    GeoJSON Feature representing a single sponge zone.
    
    Compliant with RFC 7946 GeoJSON specification.
    """
    type: str = Field(default="Feature", description="GeoJSON type")
    id: str = Field(..., description="Feature identifier (zone_id)")
    geometry: Optional[Dict[str, Any]] = Field(
        None,
        description="GeoJSON Polygon geometry with coordinates"
    )
    properties: ZoneProperties = Field(..., description="Zone metadata")
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        """Ensure type is 'Feature'."""
        if v != "Feature":
            raise ValueError('type must be "Feature"')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "Feature",
                "id": "Z001",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [80.2707, 13.0067],
                            [80.2720, 13.0067],
                            [80.2720, 13.0080],
                            [80.2707, 13.0080],
                            [80.2707, 13.0067]
                        ]
                    ]
                },
                "properties": {
                    "zone_id": "Z001",
                    "zone_name": "Adyar River Basin Zone 4",
                    "capacity_score": 85.2,
                    "capacity_category": "High",
                    "terrain_type": "River Basin",
                    "recommendation": "Priority desilting recommended"
                }
            }
        }
    )


class SpongeZoneCollection(BaseModel):
    """
    GeoJSON FeatureCollection for all sponge zones.
    
    This is the primary response format for the map endpoint.
    """
    type: str = Field(default="FeatureCollection", description="GeoJSON type")
    features: List[SpongeZoneFeature] = Field(
        ...,
        description="List of sponge zone features"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata (model version, timestamp, etc.)"
    )
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        """Ensure type is 'FeatureCollection'."""
        if v != "FeatureCollection":
            raise ValueError('type must be "FeatureCollection"')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "FeatureCollection",
                "features": [],
                "metadata": {
                    "model_version": "v1.0-unet-placeholder",
                    "generated_at": "2026-02-02T10:30:00Z",
                    "total_zones": 5
                }
            }
        }
    )


class ZoneDetailResponse(BaseModel):
    """
    Detailed response for a single zone lookup.
    """
    success: bool = Field(..., description="Whether the query was successful")
    data: Optional[SpongeZoneFeature] = Field(
        None,
        description="Zone data if found"
    )
    message: Optional[str] = Field(
        None,
        description="Error message or additional info"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {
                    "type": "Feature",
                    "id": "Z001",
                    "properties": {
                        "zone_id": "Z001",
                        "zone_name": "Adyar River Basin Zone 4",
                        "capacity_score": 85.2,
                        "capacity_category": "High"
                    }
                },
                "message": None
            }
        }
    )
