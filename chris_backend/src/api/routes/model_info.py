"""
Model Info API route for exposing ML model metadata and status.
"""
from fastapi import APIRouter, HTTPException, status, Query
from typing import Dict, Any
import logging

from src.ml.model_loader import get_model_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Models"])


# PUBLIC_INTERFACE
@router.get(
    "/models/info",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get ML model information",
    description="Retrieve metadata and status information about loaded ML models."
)
async def get_models_info(
    model_type: str = Query(
        default="all",
        description="Model type to query: 'lstm', 'unet', or 'all'",
        regex="^(lstm|unet|all)$"
    )
) -> Dict[str, Any]:
    """
    Get information about loaded ML models.
    
    Args:
        model_type: Which model(s) to query
        
    Returns:
        Dictionary with model metadata and status
    """
    try:
        logger.info(f"Model info request for: {model_type}")
        
        if model_type == "all":
            result = {
                "lstm": get_model_info("lstm"),
                "unet": get_model_info("unet")
            }
        else:
            result = {
                model_type: get_model_info(model_type)
            }
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to get model info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve model information: {str(e)}"
        )
