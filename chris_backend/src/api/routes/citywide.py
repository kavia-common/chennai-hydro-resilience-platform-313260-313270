"""
Citywide Risk API routes for aggregate flood risk data.

PUBLIC_INTERFACE: GET /api/v1/citywide-risk
Returns all citywide risk predictions with aggregate statistics, pagination, and caching.
"""
from fastapi import APIRouter, HTTPException, Query, status, Request
from typing import Optional, List
import logging

from src.schemas.citywide import CitywideRiskResponse
from src.schemas.forecast import CitywideRiskRecord
from src.utils.supabase_client import get_supabase_client, build_optimized_query
from src.utils.cache import get_cache, generate_cache_key
from src.utils.pagination import paginate_results
from src.utils.structured_logger import StructuredLogger
from src.middleware.rate_limit import get_client_ip

logger = logging.getLogger(__name__)
struct_log = StructuredLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Citywide Risk"])


# PUBLIC_INTERFACE
@router.get(
    "/citywide-risk",
    response_model=CitywideRiskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get citywide flood risk data (Paginated & Cached)",
    description="""
    Retrieve citywide flood risk predictions with aggregate statistics, pagination, and caching.
    
    **Public Endpoint** - No authentication required for read access.
    
    **Performance Features:**
    - **Caching**: Results cached for 10 minutes (600s) to reduce database load
    - **Pagination**: Support for large datasets with limit/offset parameters
    - **Optimized Queries**: Uses selective field filtering and database indexes
    
    **Use Case:**
    - Display historical and forecasted risk trends in charts
    - Highlight critical risk years
    - Show aggregate statistics (highest risk year, average score)
    
    **Query Parameters:**
    - `start_year`: Filter predictions starting from this year (optional, range: 2000-2100)
    - `end_year`: Filter predictions up to this year (optional, range: 2000-2100)
    - `risk_category`: Filter by risk level (Low, Moderate, High, Critical) (optional)
    - `limit`: Maximum items per page (1-1000, default: 50)
    - `offset`: Number of items to skip (default: 0)
    
    **Response includes:**
    - Paginated risk predictions ordered by year
    - Summary statistics (highest risk year, average risk score)
    - Pagination metadata (total count, page info)
    - Risk trend indicators
    
    **Cache Invalidation:** Cache automatically expires after 10 minutes or on data writes
    
    **Rate Limiting:** Subject to global rate limits (100 req/60s per IP)
    
    **Database Index Recommendation:** 
    CREATE INDEX idx_citywide_risk_year_category ON citywide_risk (year, risk_category, risk_score);
    """,
    responses={
        200: {
            "description": "Citywide risk data retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": [
                            {
                                "year": 2025,
                                "risk_score": 65.5,
                                "risk_category": "Moderate",
                                "predicted_rainfall_mm": 1250.5
                            }
                        ],
                        "summary": {
                            "highest_risk_year": 2027,
                            "highest_risk_score": 88.7,
                            "average_risk_score": 65.5,
                            "critical_years": [2027]
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
async def get_citywide_risk(
    request: Request,
    start_year: Optional[int] = Query(
        None,
        description="Filter predictions from this year onwards",
        ge=2000,
        le=2100
    ),
    end_year: Optional[int] = Query(
        None,
        description="Filter predictions up to this year",
        ge=2000,
        le=2100
    ),
    risk_category: Optional[str] = Query(
        None,
        description="Filter by risk category: Low, Moderate, High, Critical",
        pattern="^(Low|Moderate|High|Critical)$"
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=1000,
        description="Maximum items per page (1-1000)"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of items to skip for pagination"
    )
) -> CitywideRiskResponse:
    """
    Get citywide flood risk predictions with filtering, pagination, caching, and statistics.
    
    Public endpoint - no authentication required.
    Uses caching (10 min TTL) and optimized queries for performance.
    
    Args:
        request: FastAPI request object
        start_year: Optional start year filter (2000-2100)
        end_year: Optional end year filter (2000-2100)
        risk_category: Optional risk category filter (Low/Moderate/High/Critical)
        limit: Maximum items per page (1-1000)
        offset: Pagination offset
        
    Returns:
        CitywideRiskResponse with paginated predictions and summary statistics
        
    Raises:
        HTTPException: If database query fails or validation errors
    """
    client_ip = get_client_ip(request)
    
    # Generate cache key
    cache_key = generate_cache_key(
        "citywide_risk",
        start_year=start_year,
        end_year=end_year,
        risk_category=risk_category,
        limit=limit,
        offset=offset
    )
    
    # Try to get from cache
    cache = get_cache()
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        struct_log.info(
            "Returning cached citywide risk data",
            client_ip=client_ip,
            cache_key=cache_key
        )
        return cached_result
    
    # Validate year range if both provided
    if start_year and end_year and start_year > end_year:
        logger.warning(f"Invalid year range from {client_ip}: start_year > end_year")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_year must be less than or equal to end_year"
        )
    
    # Validate risk_category if provided (defense in depth)
    if risk_category and risk_category not in ["Low", "Moderate", "High", "Critical"]:
        logger.warning(f"Invalid risk_category from {client_ip}: {risk_category}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="risk_category must be one of: Low, Moderate, High, Critical"
        )
    
    try:
        struct_log.info(
            "Fetching citywide risk data",
            client_ip=client_ip,
            start_year=start_year,
            end_year=end_year,
            risk_category=risk_category,
            limit=limit,
            offset=offset
        )
        
        # Build filters
        filters = {}
        if risk_category:
            filters["risk_category"] = risk_category
        
        # Build optimized query with selective fields
        query = build_optimized_query(
            table_name="citywide_risk",
            select_fields=[
                "year", "risk_score", "risk_category", 
                "predicted_rainfall_mm", "oni_anomaly", "iod_anomaly",
                "confidence"
            ],
            filters=filters,
            order_by="year",
            order_desc=False,
            limit=limit,
            offset=offset
        )
        
        # Apply year range filters (not in build_optimized_query for flexibility)
        if start_year:
            query = query.gte("year", start_year)
        if end_year:
            query = query.lte("year", end_year)
        
        response = query.execute()
        
        # Get total count for pagination metadata (separate query)
        count_query = get_supabase_client().table("citywide_risk").select("year", count="exact")
        if start_year:
            count_query = count_query.gte("year", start_year)
        if end_year:
            count_query = count_query.lte("year", end_year)
        if risk_category:
            count_query = count_query.eq("risk_category", risk_category)
        
        count_response = count_query.execute()
        total_count = count_response.count if hasattr(count_response, 'count') else len(response.data)
        
        if not response.data:
            struct_log.info(
                "No citywide risk data found",
                client_ip=client_ip,
                filters_applied=True
            )
            empty_response = CitywideRiskResponse(
                success=True,
                data=[],
                summary={
                    "total_years": 0,
                    "message": "No risk data found. Ensure citywide_risk table is populated."
                },
                message="No data available for the specified filters."
            )
            # Cache empty result with shorter TTL
            cache.set(cache_key, empty_response, ttl_seconds=60)
            return empty_response
        
        # Convert to Pydantic models
        records: List[CitywideRiskRecord] = [
            CitywideRiskRecord(**record) for record in response.data
        ]
        
        # Calculate aggregate statistics
        risk_scores = [r.risk_score for r in records]
        critical_years = [r.year for r in records if r.risk_category == "Critical"]
        high_years = [r.year for r in records if r.risk_category == "High"]
        
        highest_risk_record = max(records, key=lambda r: r.risk_score)
        
        # Build pagination metadata
        pagination_data = paginate_results(
            data=records,
            limit=limit,
            offset=offset,
            total_count=total_count
        )
        
        summary = {
            "total_years": total_count,
            "returned_years": len(records),
            "highest_risk_year": highest_risk_record.year,
            "highest_risk_score": highest_risk_record.risk_score,
            "highest_risk_category": highest_risk_record.risk_category,
            "average_risk_score": round(sum(risk_scores) / len(risk_scores), 2),
            "critical_years": critical_years,
            "high_risk_years": high_years,
            "year_range": {
                "start": min(r.year for r in records),
                "end": max(r.year for r in records)
            },
            "pagination": pagination_data["pagination"]
        }
        
        struct_log.info(
            "Citywide risk data retrieved successfully",
            client_ip=client_ip,
            total_count=total_count,
            returned_count=len(records)
        )
        
        result = CitywideRiskResponse(
            success=True,
            data=records,
            summary=summary,
            message=None
        )
        
        # Cache result for 10 minutes
        cache.set(cache_key, result, ttl_seconds=600)
        
        return result
    
    except Exception as e:
        struct_log.error(
            "Error fetching citywide risk data",
            client_ip=client_ip,
            error=str(e)
        )
        logger.error(f"Error fetching citywide risk data from {client_ip}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve citywide risk data: {str(e)}"
        )
