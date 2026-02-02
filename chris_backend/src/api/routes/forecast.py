"""
Forecast API routes for temporal flood risk prediction.

PUBLIC_INTERFACE: POST /api/v1/forecast/
Generates multi-year flood risk forecasts using LSTM predictions stored in Supabase.
"""
from fastapi import APIRouter, HTTPException, status
from datetime import datetime
from typing import List
import logging

from src.schemas.forecast import ForecastRequest, ForecastResponse, CitywideRiskRecord
from src.utils.supabase_client import get_supabase_client
from src.ml.model_loader import predict_flood_risk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Forecast"])


# PUBLIC_INTERFACE
@router.post(
    "/forecast/",
    response_model=ForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate flood risk forecast",
    description="""
    Generate a multi-year flood risk forecast for Chennai using LSTM-based predictions.
    
    **Workflow:**
    1. Queries the `citywide_risk` table in Supabase for existing predictions
    2. Returns forecasts for the requested number of years
    3. If ML model is available, can generate new predictions (future enhancement)
    
    **Response includes:**
    - Yearly risk scores (0-100)
    - Risk categories (Low, Moderate, High, Critical)
    - Climate driver data (ONI, IOD anomalies)
    - Predicted rainfall amounts
    - Model confidence scores
    
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
        500: {"description": "Database error or server error"}
    }
)
async def generate_forecast(request: ForecastRequest) -> ForecastResponse:
    """
    Generate flood risk forecast for the specified number of years.
    
    Args:
        request: ForecastRequest with years and options
        
    Returns:
        ForecastResponse with predictions and metadata
        
    Raises:
        HTTPException: If database query fails
    """
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Query existing predictions from database
        current_year = datetime.now().year
        end_year = current_year + request.years
        
        logger.info(f"Fetching predictions for years {current_year}-{end_year}")
        
        response = supabase.table("citywide_risk") \
            .select("*") \
            .gte("year", current_year) \
            .lte("year", end_year) \
            .order("year") \
            .execute()
        
        if not response.data:
            # No predictions found - could generate using ML model in future
            logger.warning("No predictions found in database")
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
        logger.error(f"Error generating forecast: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate forecast: {str(e)}"
        )
