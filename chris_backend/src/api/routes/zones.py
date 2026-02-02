"""
Sponge Zone API routes for spatial terrain analysis.

PUBLIC_INTERFACE: GET /api/v1/map/sponge-zones
PUBLIC_INTERFACE: GET /api/v1/zone-details
Returns GeoJSON-compliant sponge zone mapping data from U-Net satellite analysis.
"""
from fastapi import APIRouter, HTTPException, Query, status
from datetime import datetime
from typing import Optional, List
import logging

from src.schemas.zone import (
    SpongeZoneCollection,
    SpongeZoneFeature,
    ZoneProperties,
    ZoneDetailResponse
)
from src.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Zones"])


def _convert_to_geojson_feature(zone_record: dict) -> SpongeZoneFeature:
    """
    Convert Supabase zone_risk record to GeoJSON Feature.
    
    Args:
        zone_record: Raw database record from zone_risk table
        
    Returns:
        SpongeZoneFeature with proper GeoJSON structure
    """
    # Extract geometry (stored as JSONB in Supabase)
    geometry = zone_record.get("geometry")
    
    # Build properties
    properties = ZoneProperties(
        zone_id=zone_record["zone_id"],
        zone_name=zone_record["zone_name"],
        capacity_score=zone_record["capacity_score"],
        capacity_category=zone_record["capacity_category"],
        vv_amplitude=zone_record.get("vv_amplitude"),
        vh_backscatter=zone_record.get("vh_backscatter"),
        mndwi=zone_record.get("mndwi"),
        ndvi=zone_record.get("ndvi"),
        terrain_type=zone_record.get("terrain_type"),
        recommendation=zone_record.get("recommendation")
    )
    
    return SpongeZoneFeature(
        type="Feature",
        id=zone_record["zone_id"],
        geometry=geometry,
        properties=properties
    )


# PUBLIC_INTERFACE
@router.get(
    "/map/sponge-zones",
    response_model=SpongeZoneCollection,
    status_code=status.HTTP_200_OK,
    summary="Get sponge zones GeoJSON",
    description="""
    Retrieve all sponge zones as a GeoJSON FeatureCollection for map visualization.
    
    **Data Source:** U-Net semantic segmentation of Sentinel-1/2 satellite imagery
    
    **Use Case:** 
    - Render zones on Leaflet/Mapbox map
    - Color-code by capacity_category (High=Green, Moderate=Yellow, Low=Red)
    - Display recommendations on click
    
    **Filters:**
    - `capacity_category`: Filter by Low/Moderate/High capacity
    - `terrain_type`: Filter by terrain classification (e.g., 'Wetland')
    
    **Response Format:** RFC 7946 compliant GeoJSON FeatureCollection
    
    **Note:** Geometry coordinates are in WGS84 (EPSG:4326) format [longitude, latitude].
    """,
    responses={
        200: {
            "description": "GeoJSON FeatureCollection of sponge zones",
            "content": {
                "application/json": {
                    "example": {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "id": "Z001",
                                "geometry": {
                                    "type": "Polygon",
                                    "coordinates": [[[80.27, 13.00], [80.28, 13.00]]]
                                },
                                "properties": {
                                    "zone_id": "Z001",
                                    "zone_name": "Adyar River Basin",
                                    "capacity_score": 85.2,
                                    "capacity_category": "High"
                                }
                            }
                        ],
                        "metadata": {
                            "total_zones": 5
                        }
                    }
                }
            }
        },
        500: {"description": "Database error"}
    }
)
async def get_sponge_zones(
    capacity_category: Optional[str] = Query(
        None,
        description="Filter by capacity category: Low, Moderate, High"
    ),
    terrain_type: Optional[str] = Query(
        None,
        description="Filter by terrain type (e.g., 'Wetland', 'Marsh')"
    )
) -> SpongeZoneCollection:
    """
    Retrieve all sponge zones as GeoJSON FeatureCollection.
    
    Args:
        capacity_category: Optional filter for capacity level
        terrain_type: Optional filter for terrain classification
        
    Returns:
        GeoJSON FeatureCollection with all zones
        
    Raises:
        HTTPException: If database query fails
    """
    try:
        supabase = get_supabase_client()
        
        # Build query
        query = supabase.table("zone_risk").select("*")
        
        # Apply filters
        if capacity_category:
            query = query.eq("capacity_category", capacity_category)
        if terrain_type:
            query = query.eq("terrain_type", terrain_type)
        
        # Order by capacity score (highest first)
        query = query.order("capacity_score", desc=True)
        
        response = query.execute()
        
        if not response.data:
            logger.warning("No sponge zones found in database")
            return SpongeZoneCollection(
                type="FeatureCollection",
                features=[],
                metadata={
                    "model_version": "v1.0-unet-precomputed",
                    "generated_at": datetime.utcnow().isoformat(),
                    "total_zones": 0,
                    "message": "No zones found. Ensure zone_risk table is populated."
                }
            )
        
        # Convert to GeoJSON features
        features: List[SpongeZoneFeature] = [
            _convert_to_geojson_feature(record) for record in response.data
        ]
        
        return SpongeZoneCollection(
            type="FeatureCollection",
            features=features,
            metadata={
                "model_version": "v1.0-unet-precomputed",
                "generated_at": datetime.utcnow().isoformat(),
                "total_zones": len(features),
                "filters_applied": {
                    "capacity_category": capacity_category,
                    "terrain_type": terrain_type
                }
            }
        )
    
    except Exception as e:
        logger.error(f"Error fetching sponge zones: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sponge zones: {str(e)}"
        )


# PUBLIC_INTERFACE
@router.get(
    "/zone-details",
    response_model=ZoneDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get specific zone details",
    description="""
    Retrieve detailed information for a specific sponge zone by zone_id.
    
    **Use Case:** 
    - Display detailed popup when user clicks a zone on the map
    - Show satellite indices (MNDWI, NDVI, VV/VH backscatter)
    - Display city planner recommendations
    
    **Query Parameters:**
    - `zone_id` (required): Zone identifier (e.g., 'Z001')
    """,
    responses={
        200: {"description": "Zone details retrieved successfully"},
        404: {"description": "Zone not found"},
        500: {"description": "Database error"}
    }
)
async def get_zone_details(
    zone_id: str = Query(
        ...,
        description="Zone identifier (e.g., 'Z001')",
        min_length=1
    )
) -> ZoneDetailResponse:
    """
    Get detailed information for a specific sponge zone.
    
    Args:
        zone_id: Zone identifier to lookup
        
    Returns:
        ZoneDetailResponse with complete zone data
        
    Raises:
        HTTPException: If zone not found or database error
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("zone_risk") \
            .select("*") \
            .eq("zone_id", zone_id) \
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone '{zone_id}' not found"
            )
        
        zone_record = response.data[0]
        feature = _convert_to_geojson_feature(zone_record)
        
        return ZoneDetailResponse(
            success=True,
            data=feature,
            message=None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching zone details: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve zone details: {str(e)}"
        )
