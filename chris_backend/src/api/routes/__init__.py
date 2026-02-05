"""
API routes package for CHRIS backend.
"""
from .forecast import router as forecast_router
from .zones import router as zones_router
from .citywide import router as citywide_router
from .model_info import router as model_info_router

__all__ = ["forecast_router", "zones_router", "citywide_router", "model_info_router"]
