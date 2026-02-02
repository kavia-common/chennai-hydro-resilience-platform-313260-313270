"""
Citywide Risk API routes for aggregate flood risk data.

PUBLIC_INTERFACE: GET /api/v1/citywide-risk
Returns all citywide risk predictions with aggregate statistics.
"""
from fastapi import APIRouter, HTTPException, Query, status, Request
from typing import Optional, List
import logging

from src.schemas.citywide import CitywideRiskResponse
from src.schemas.forecast import CitywideRiskRecord
from src.utils.supabase_client import get_supabase_client
from src.middleware.rate_limit import get_client_ip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Citywide Risk"])


# PUBLIC_INTERFACE
@router.get(
    "/citywide-risk",
    response_model=CitywideRiskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get citywide flood risk data",
    description="""
    Retrieve all citywide flood risk predictions with aggregate statistics.
    
    **Public Endpoint** - No authentication required for read access.
    
    **Use Case:**
    - Display historical and forecasted risk trends in charts
    - Highlight critical risk years
    - Show aggregate statistics (highest risk year, average score)
    
    **Query Parameters:**
    - `start_year`: Filter predictions starting from this year (optional, range: 2000-2100)
    - `end_year`: Filter predictions up to this year (optional, range: 2000-2100)
    - `risk_category`: Filter by risk level (Low, Moderate, High, Critical) (optional)
    
    **Response includes:**
    - All risk predictions ordered by year
    - Summary statistics (highest risk year, average risk score)
    - Risk trend indicators
    
    **Rate Limiting:** Subject to global rate limits (100 req/60s per IP)
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
    )
) -> CitywideRiskResponse:
    """
    Get all citywide flood risk predictions with filtering and statistics.
    
    Public endpoint - no authentication required.
    
    Args:
        request: FastAPI request object
        start_year: Optional start year filter (2000-2100)
        end_year: Optional end year filter (2000-2100)
        risk_category: Optional risk category filter (Low/Moderate/High/Critical)
        
    Returns:
        CitywideRiskResponse with predictions and summary statistics
        
    Raises:
        HTTPException: If database query fails or validation errors
    """
    client_ip = get_client_ip(request)
    
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
        supabase = get_supabase_client()
        
        # Build query
        query = supabase.table("citywide_risk").select("*")
        
        # Apply filters
        if start_year:
            query = query.gte("year", start_year)
        if end_year:
            query = query.lte("year", end_year)
        if risk_category:
            query = query.eq("risk_category", risk_category)
        
        # Order by year
        query = query.order("year")
        
        response = query.execute()
        
        if not response.data:
            logger.info(f"No citywide risk data found for filters: {client_ip}")
            return CitywideRiskResponse(
                success=True,
                data=[],
                summary={
                    "total_years": 0,
                    "message": "No risk data found. Ensure citywide_risk table is populated."
                },
                message="No data available for the specified filters."
            )
        
        # Convert to Pydantic models
        records: List[CitywideRiskRecord] = [
            CitywideRiskRecord(**record) for record in response.data
        ]
        
        # Calculate aggregate statistics
        risk_scores = [r.risk_score for r in records]
        critical_years = [r.year for r in records if r.risk_category == "Critical"]
        high_years = [r.year for r in records if r.risk_category == "High"]
        
        highest_risk_record = max(records, key=lambda r: r.risk_score)
        
        summary = {
            "total_years": len(records),
            "highest_risk_year": highest_risk_record.year,
            "highest_risk_score": highest_risk_record.risk_score,
            "highest_risk_category": highest_risk_record.risk_category,
            "average_risk_score": round(sum(risk_scores) / len(risk_scores), 2),
            "critical_years": critical_years,
            "high_risk_years": high_years,
            "year_range": {
                "start": min(r.year for r in records),
                "end": max(r.year for r in records)
            }
        }
        
        logger.info(f"Citywide risk data retrieved successfully for {client_ip}: {len(records)} records")
        
        return CitywideRiskResponse(
            success=True,
            data=records,
            summary=summary,
            message=None
        )
    
    except Exception as e:
        logger.error(f"Error fetching citywide risk data from {client_ip}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve citywide risk data: {str(e)}"
        )
