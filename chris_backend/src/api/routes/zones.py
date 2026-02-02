"""
Sponge Zone API routes for spatial terrain analysis.

PUBLIC_INTERFACE: GET /api/v1/map/sponge-zones
PUBLIC_INTERFACE: GET /api/v1/zone-details
Returns GeoJSON-compliant sponge zone mapping data from U-Net satellite analysis.
"""
from fastapi import APIRouter, HTTPException, Query, status, Request
from datetime import datetime
from typing import Optional, List
import logging
import re

from src.schemas.zone import (
    SpongeZoneCollection,
    SpongeZoneFeature,
    ZoneProperties,
    ZoneDetailResponse
)
from src.utils.supabase_client import get_supabase_client
from src.middleware.rate_limit import get_client_ip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Zones"])


def _sanitize_zone_id(zone_id: str) -> str:
    """
    Sanitize zone_id to prevent injection attacks.
    
    Args:
        zone_id: Raw zone ID from request
        
    Returns:
        Sanitized zone ID
        
    Raises:
        ValueError: If zone_id contains invalid characters
    """
    # Remove any characters that aren't alphanumeric, underscore, or dash
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', zone_id)
    
    if sanitized != zone_id:
        raise ValueError("Invalid characters in zone_id. Only alphanumeric, underscore, and dash allowed.")
    
    if len(sanitized) == 0 or len(sanitized) > 20:
        raise ValueError("zone_id must be between 1 and 20 characters")
    
    return sanitized


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
    
    **Public Endpoint** - No authentication required for read access.
    
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
    
    **Rate Limiting:** Subject to global rate limits (100 req/60s per IP)
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
        422: {"description": "Validation error - Invalid query parameters"},
        429: {"description": "Too many requests - Rate limit exceeded"},
        500: {"description": "Database error"}
    }
)
async def get_sponge_zones(
    request: Request,
    capacity_category: Optional[str] = Query(
        None,
        description="Filter by capacity category: Low, Moderate, High",
        pattern="^(Low|Moderate|High)$"
    ),
    terrain_type: Optional[str] = Query(
        None,
        description="Filter by terrain type (e.g., 'Wetland', 'Marsh')",
        max_length=100
    )
) -> SpongeZoneCollection:
    """
    Retrieve all sponge zones as GeoJSON FeatureCollection.
    
    Public endpoint - no authentication required.
    
    Args:
        request: FastAPI request object
        capacity_category: Optional filter for capacity level
        terrain_type: Optional filter for terrain classification
        
    Returns:
        GeoJSON FeatureCollection with all zones
        
    Raises:
        HTTPException: If database query fails or validation errors
    """
    client_ip = get_client_ip(request)
    
    # Validate capacity_category if provided (defense in depth)
    if capacity_category and capacity_category not in ["Low", "Moderate", "High"]:
        logger.warning(f"Invalid capacity_category from {client_ip}: {capacity_category}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="capacity_category must be one of: Low, Moderate, High"
        )
    
    # Sanitize terrain_type if provided
    if terrain_type:
        # Remove any potentially dangerous characters
        terrain_type = re.sub(r'[^\w\s-]', '', terrain_type).strip()
        if len(terrain_type) > 100:
            terrain_type = terrain_type[:100]
    
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
            logger.info(f"No sponge zones found for filters from {client_ip}")
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
        
        logger.info(f"Sponge zones retrieved successfully for {client_ip}: {len(features)} zones")
        
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
        logger.error(f"Error fetching sponge zones from {client_ip}: {str(e)}", exc_info=True)
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
    
    **Public Endpoint** - No authentication required for read access.
    
    **Use Case:** 
    - Display detailed popup when user clicks a zone on the map
    - Show satellite indices (MNDWI, NDVI, VV/VH backscatter)
    - Display city planner recommendations
    
    **Query Parameters:**
    - `zone_id` (required): Zone identifier (e.g., 'Z001') - must be alphanumeric with optional dash/underscore
    
    **Rate Limiting:** Subject to global rate limits (100 req/60s per IP)
    """,
    responses={
        200: {"description": "Zone details retrieved successfully"},
        404: {"description": "Zone not found"},
        422: {"description": "Validation error - Invalid zone_id format"},
        429: {"description": "Too many requests - Rate limit exceeded"},
        500: {"description": "Database error"}
    }
)
async def get_zone_details(
    request: Request,
    zone_id: str = Query(
        ...,
        description="Zone identifier (e.g., 'Z001')",
        min_length=1,
        max_length=20
    )
) -> ZoneDetailResponse:
    """
    Get detailed information for a specific sponge zone.
    
    Public endpoint - no authentication required.
    
    Args:
        request: FastAPI request object
        zone_id: Zone identifier to lookup
        
    Returns:
        ZoneDetailResponse with complete zone data
        
    Raises:
        HTTPException: If zone not found, validation error, or database error
    """
    client_ip = get_client_ip(request)
    
    # Sanitize zone_id
    try:
        zone_id = _sanitize_zone_id(zone_id)
    except ValueError as e:
        logger.warning(f"Invalid zone_id from {client_ip}: {zone_id} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("zone_risk") \
            .select("*") \
            .eq("zone_id", zone_id) \
            .execute()
        
        if not response.data:
            logger.info(f"Zone not found from {client_ip}: {zone_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone '{zone_id}' not found"
            )
        
        zone_record = response.data[0]
        feature = _convert_to_geojson_feature(zone_record)
        
        logger.info(f"Zone details retrieved successfully for {client_ip}: {zone_id}")
        
        return ZoneDetailResponse(
            success=True,
            data=feature,
            message=None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching zone details from {client_ip}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve zone details: {str(e)}"
        )
