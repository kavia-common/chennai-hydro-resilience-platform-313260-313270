"""
Pydantic schemas for sponge zone mapping endpoints.

These models define the GeoJSON-compliant structure for spatial
U-Net-based sponge zone data.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ZoneProperties(BaseModel):
    """
    Properties for a single sponge zone (GeoJSON Feature properties).
    """
    zone_id: str = Field(..., description="Zone identifier (e.g., 'Z001')")
    zone_name: str = Field(..., description="Human-readable zone name")
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
        description="Sentinel-1 VV polarization amplitude (dB)"
    )
    vh_backscatter: Optional[float] = Field(
        None,
        description="Sentinel-1 VH backscatter coefficient (dB)"
    )
    mndwi: Optional[float] = Field(
        None,
        ge=-1.0,
        le=1.0,
        description="Modified Normalized Difference Water Index"
    )
    ndvi: Optional[float] = Field(
        None,
        ge=-1.0,
        le=1.0,
        description="Normalized Difference Vegetation Index"
    )
    terrain_type: Optional[str] = Field(
        None,
        description="Terrain classification (e.g., 'Wetland', 'Marsh')"
    )
    recommendation: Optional[str] = Field(
        None,
        description="Action recommendation for city planners"
    )


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

    class Config:
        json_schema_extra = {
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

    class Config:
        json_schema_extra = {
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

    class Config:
        json_schema_extra = {
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
