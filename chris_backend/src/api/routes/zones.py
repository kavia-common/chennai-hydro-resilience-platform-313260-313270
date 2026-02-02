"""
Sponge Zone API routes for spatial terrain analysis.

PUBLIC_INTERFACE: GET /api/v1/map/sponge-zones (Paginated & Cached)
PUBLIC_INTERFACE: GET /api/v1/zone-details (Cached)
Returns GeoJSON-compliant sponge zone mapping data from U-Net satellite analysis with performance optimizations.
"""
from fastapi import APIRouter, HTTPException, Query, status, Request, Path
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
from src.utils.supabase_client import get_supabase_client, build_optimized_query
from src.utils.cache import get_cache, generate_cache_key
from src.utils.pagination import paginate_results
from src.utils.structured_logger import StructuredLogger
from src.middleware.rate_limit import get_client_ip

logger = logging.getLogger(__name__)
struct_log = StructuredLogger(__name__)

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
    summary="Get sponge zones GeoJSON (Paginated & Cached)",
    description="""
    Retrieve sponge zones as a GeoJSON FeatureCollection with pagination and caching for map visualization.
    
    **Public Endpoint** - No authentication required for read access.
    
    **Performance Features:**
    - **Caching**: Results cached for 10 minutes (600s) to reduce database load
    - **Pagination**: Support for large zone datasets with limit/offset
    - **Optimized Queries**: Uses selective field filtering and database indexes
    
    **Data Source:** U-Net semantic segmentation of Sentinel-1/2 satellite imagery
    
    **Use Case:** 
    - Render zones on Leaflet/Mapbox map
    - Color-code by capacity_category (High=Green, Moderate=Yellow, Low=Red)
    - Display recommendations on click
    
    **Filters:**
    - `capacity_category`: Filter by Low/Moderate/High capacity
    - `terrain_type`: Filter by terrain classification (e.g., 'Wetland')
    - `limit`: Maximum zones per page (1-500, default: 100)
    - `offset`: Number of zones to skip (default: 0)
    
    **Response Format:** RFC 7946 compliant GeoJSON FeatureCollection
    
    **Note:** Geometry coordinates are in WGS84 (EPSG:4326) format [longitude, latitude].
    
    **Cache Invalidation:** Cache expires after 10 minutes or on zone data writes
    
    **Rate Limiting:** Subject to global rate limits (100 req/60s per IP)
    
    **Database Index Recommendation:**
    CREATE INDEX idx_zone_risk_category_score ON zone_risk (capacity_category, capacity_score DESC);
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
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Maximum zones per page (1-500)"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of zones to skip for pagination"
    )
) -> SpongeZoneCollection:
    """
    Retrieve sponge zones as GeoJSON FeatureCollection with pagination and caching.
    
    Public endpoint - no authentication required.
    Uses caching (10 min TTL) and optimized queries for performance.
    
    Args:
        request: FastAPI request object
        capacity_category: Optional filter for capacity level
        terrain_type: Optional filter for terrain classification
        limit: Maximum zones per page
        offset: Pagination offset
        
    Returns:
        GeoJSON FeatureCollection with paginated zones
        
    Raises:
        HTTPException: If database query fails or validation errors
    """
    client_ip = get_client_ip(request)
    
    # Generate cache key
    cache_key = generate_cache_key(
        "sponge_zones",
        capacity_category=capacity_category,
        terrain_type=terrain_type,
        limit=limit,
        offset=offset
    )
    
    # Try to get from cache
    cache = get_cache()
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        struct_log.info(
            "Returning cached sponge zones",
            client_ip=client_ip,
            cache_key=cache_key
        )
        return cached_result
    
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
        struct_log.info(
            "Fetching sponge zones",
            client_ip=client_ip,
            capacity_category=capacity_category,
            terrain_type=terrain_type,
            limit=limit,
            offset=offset
        )
        
        # Build filters
        filters = {}
        if capacity_category:
            filters["capacity_category"] = capacity_category
        if terrain_type:
            filters["terrain_type"] = terrain_type
        
        # Build optimized query
        query = build_optimized_query(
            table_name="zone_risk",
            select_fields=None,  # Need all fields including geometry for GeoJSON
            filters=filters,
            order_by="capacity_score",
            order_desc=True,
            limit=limit,
            offset=offset
        )
        
        response = query.execute()
        
        # Get total count for pagination
        count_query = get_supabase_client().table("zone_risk").select("zone_id", count="exact")
        if capacity_category:
            count_query = count_query.eq("capacity_category", capacity_category)
        if terrain_type:
            count_query = count_query.eq("terrain_type", terrain_type)
        
        count_response = count_query.execute()
        total_count = count_response.count if hasattr(count_response, 'count') else len(response.data)
        
        if not response.data:
            struct_log.info(
                "No sponge zones found",
                client_ip=client_ip,
                filters_applied=True
            )
            empty_response = SpongeZoneCollection(
                type="FeatureCollection",
                features=[],
                metadata={
                    "model_version": "v1.0-unet-precomputed",
                    "generated_at": datetime.utcnow().isoformat(),
                    "total_zones": 0,
                    "message": "No zones found. Ensure zone_risk table is populated."
                }
            )
            # Cache empty result with shorter TTL
            cache.set(cache_key, empty_response, ttl_seconds=60)
            return empty_response
        
        # Convert to GeoJSON features
        features: List[SpongeZoneFeature] = [
            _convert_to_geojson_feature(record) for record in response.data
        ]
        
        # Build pagination metadata
        pagination_data = paginate_results(
            data=features,
            limit=limit,
            offset=offset,
            total_count=total_count
        )
        
        struct_log.info(
            "Sponge zones retrieved successfully",
            client_ip=client_ip,
            total_count=total_count,
            returned_count=len(features)
        )
        
        result = SpongeZoneCollection(
            type="FeatureCollection",
            features=features,
            metadata={
                "model_version": "v1.0-unet-precomputed",
                "generated_at": datetime.utcnow().isoformat(),
                "total_zones": total_count,
                "returned_zones": len(features),
                "filters_applied": {
                    "capacity_category": capacity_category,
                    "terrain_type": terrain_type
                },
                "pagination": pagination_data["pagination"]
            }
        )
        
        # Cache result for 10 minutes
        cache.set(cache_key, result, ttl_seconds=600)
        
        return result
    
    except Exception as e:
        struct_log.error(
            "Error fetching sponge zones",
            client_ip=client_ip,
            error=str(e)
        )
        logger.error(f"Error fetching sponge zones from {client_ip}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sponge zones: {str(e)}"
        )


# PUBLIC_INTERFACE
@router.get(
    "/map/sponge-zones/{zone_id}/details",
    response_model=ZoneDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get specific zone details (Cached)",
    description="""
    Retrieve detailed information for a specific sponge zone by zone_id with caching.
    
    **Public Endpoint** - No authentication required for read access.
    
    **Performance Features:**
    - **Caching**: Results cached for 15 minutes (900s) per zone
    - **Optimized Queries**: Direct lookup by zone_id (indexed primary key)
    
    **Use Case:** 
    - Display detailed popup when user clicks a zone on the map
    - Show satellite indices (MNDWI, NDVI, VV/VH backscatter)
    - Display city planner recommendations
    
    **Path Parameters:**
    - `zone_id` (required): Zone identifier (e.g., 'Z001') - must be alphanumeric with optional dash/underscore
    
    **Cache Invalidation:** Cache expires after 15 minutes or on zone data updates
    
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
    zone_id: str = Path(
        ...,
        description="Zone identifier (e.g., 'Z001')",
        min_length=1,
        max_length=20
    )
) -> ZoneDetailResponse:
    """
    Get detailed information for a specific sponge zone with caching.
    
    Public endpoint - no authentication required.
    Uses caching (15 min TTL) for individual zone lookups.
    
    Args:
        request: FastAPI request object
        zone_id: Zone identifier to lookup (from path parameter)
        
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
        struct_log.warning(
            "Invalid zone_id",
            client_ip=client_ip,
            zone_id=zone_id,
            error=str(e)
        )
        logger.warning(f"Invalid zone_id from {client_ip}: {zone_id} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    
    # Generate cache key
    cache_key = generate_cache_key("zone_detail", zone_id=zone_id)
    
    # Try to get from cache
    cache = get_cache()
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        struct_log.info(
            "Returning cached zone details",
            client_ip=client_ip,
            zone_id=zone_id
        )
        return cached_result
    
    try:
        struct_log.info(
            "Fetching zone details",
            client_ip=client_ip,
            zone_id=zone_id
        )
        
        supabase = get_supabase_client()
        
        response = supabase.table("zone_risk") \
            .select("*") \
            .eq("zone_id", zone_id) \
            .execute()
        
        if not response.data:
            struct_log.info(
                "Zone not found",
                client_ip=client_ip,
                zone_id=zone_id
            )
            logger.info(f"Zone not found from {client_ip}: {zone_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone '{zone_id}' not found"
            )
        
        zone_record = response.data[0]
        feature = _convert_to_geojson_feature(zone_record)
        
        struct_log.info(
            "Zone details retrieved successfully",
            client_ip=client_ip,
            zone_id=zone_id
        )
        logger.info(f"Zone details retrieved successfully for {client_ip}: {zone_id}")
        
        result = ZoneDetailResponse(
            success=True,
            data=feature,
            message=None
        )
        
        # Cache result for 15 minutes
        cache.set(cache_key, result, ttl_seconds=900)
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        struct_log.error(
            "Error fetching zone details",
            client_ip=client_ip,
            zone_id=zone_id,
            error=str(e)
        )
        logger.error(f"Error fetching zone details from {client_ip}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve zone details: {str(e)}"
        )
