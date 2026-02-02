"""
Forecast API routes for temporal flood risk prediction.

PUBLIC_INTERFACE: POST /api/v1/forecast/
Generates multi-year flood risk forecasts using LSTM predictions stored in Supabase.
PROTECTED: Requires JWT authentication.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Request
from datetime import datetime
from typing import List, Dict, Any
import logging

from src.schemas.forecast import ForecastRequest, ForecastResponse, CitywideRiskRecord
from src.utils.supabase_client import get_supabase_client
from src.ml.model_loader import predict_flood_risk
from src.middleware.auth import get_current_user
from src.middleware.rate_limit import get_client_ip
from src.utils.security_logger import log_auth_success, log_suspicious_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Forecast"])


# PUBLIC_INTERFACE
@router.post(
    "/forecast/",
    response_model=ForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate flood risk forecast (Protected)",
    description="""
    Generate a multi-year flood risk forecast for Chennai using LSTM-based predictions.
    
    **🔒 PROTECTED ENDPOINT - Requires JWT Authentication**
    
    **Authentication:**
    - Requires valid Supabase JWT token in Authorization header
    - Format: `Authorization: Bearer <your_jwt_token>`
    - User context (user_id) is derived from JWT, not client input
    
    **Workflow:**
    1. Validates JWT token and extracts authenticated user_id
    2. Queries the `citywide_risk` table in Supabase for existing predictions
    3. Returns forecasts for the requested number of years
    4. If ML model is available, can generate new predictions (future enhancement)
    
    **Response includes:**
    - Yearly risk scores (0-100)
    - Risk categories (Low, Moderate, High, Critical)
    - Climate driver data (ONI, IOD anomalies)
    - Predicted rainfall amounts
    - Model confidence scores
    
    **Input Validation:**
    - `years`: Must be between 1 and 10 (inclusive)
    - `include_climate_factors`: Boolean flag
    
    **Note:** Currently returns pre-computed predictions from the database.
    Future versions will support real-time ML inference when .pkl/.onnx models are uploaded.
    """,
    responses={
        200: {
            "description": "Forecast generated successfully",
            "content": {
                "application/json": {
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
                        "generated_at": "2026-02-02T10:30:00Z"
                    }
                }
            }
        },
        401: {"description": "Unauthorized - Invalid or missing JWT token"},
        422: {"description": "Validation error - Invalid input parameters"},
        429: {"description": "Too many requests - Rate limit exceeded"},
        500: {"description": "Database error or server error"}
    }
)
async def generate_forecast(
    request: ForecastRequest,
    http_request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
) -> ForecastResponse:
    """
    Generate flood risk forecast for the specified number of years.
    
    Protected endpoint requiring JWT authentication.
    
    Args:
        request: ForecastRequest with years and options
        http_request: FastAPI request object
        user: Authenticated user payload from JWT token
        
    Returns:
        ForecastResponse with predictions and metadata
        
    Raises:
        HTTPException: If database query fails or validation errors
    """
    user_id = user.get("sub")
    client_ip = get_client_ip(http_request)
    
    # Log successful authentication
    log_auth_success(user_id, client_ip, "/api/v1/forecast/")
    
    logger.info(f"Forecast request from authenticated user {user_id}: years={request.years}")
    
    # Additional input validation (defense in depth)
    if request.years < 1 or request.years > 10:
        log_suspicious_activity(
            "invalid_forecast_years",
            client_ip,
            {"user_id": user_id, "years": request.years}
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Years parameter must be between 1 and 10"
        )
    
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Query existing predictions from database
        current_year = datetime.now().year
        end_year = current_year + request.years
        
        logger.info(f"Fetching predictions for years {current_year}-{end_year} (user: {user_id})")
        
        # Query with RLS consideration - Supabase will automatically apply RLS policies
        response = supabase.table("citywide_risk") \
            .select("*") \
            .gte("year", current_year) \
            .lte("year", end_year) \
            .order("year") \
            .execute()
        
        if not response.data:
            # No predictions found - could generate using ML model in future
            logger.warning(f"No predictions found in database for user {user_id}")
            ml_predictions = predict_flood_risk(years=request.years)
            
            if not ml_predictions:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No predictions available for years {current_year}-{end_year}. "
                           "Please ensure the database is populated or upload an LSTM model."
                )
        
        # Convert database records to Pydantic models
        predictions: List[CitywideRiskRecord] = [
            CitywideRiskRecord(**record) for record in response.data
        ]
        
        # Filter climate factors if not requested
        if not request.include_climate_factors:
            for pred in predictions:
                pred.oni_anomaly = None
                pred.iod_anomaly = None
        
        logger.info(f"Successfully generated forecast for user {user_id}: {len(predictions)} years")
        
        return ForecastResponse(
            success=True,
            data=predictions,
            model_version="v1.0-lstm-precomputed",
            generated_at=datetime.utcnow(),
            message="Using pre-computed predictions from database. "
                    "Upload LSTM model (.pkl/.onnx) for real-time inference."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating forecast for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate forecast: {str(e)}"
        )
