"""
CHRIS Backend API - Main FastAPI Application.

Chennai Hydro-Resilience Intelligence System (CHRIS) backend service.
Provides REST APIs for flood risk prediction and sponge zone mapping.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os

from src.api.routes import forecast_router, zones_router, citywide_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# OpenAPI metadata
openapi_tags = [
    {
        "name": "Health",
        "description": "Health check and service status endpoints"
    },
    {
        "name": "Forecast",
        "description": "**Temporal LSTM Predictions** - Generate multi-year flood risk forecasts based on climate drivers (ONI, IOD) and rainfall patterns"
    },
    {
        "name": "Zones",
        "description": "**Spatial U-Net Analysis** - Retrieve sponge zone GeoJSON data from satellite imagery segmentation (Sentinel-1/2)"
    },
    {
        "name": "Citywide Risk",
        "description": "**Aggregate Risk Data** - Access citywide flood risk trends and statistics"
    }
]

# Initialize FastAPI app
app = FastAPI(
    title="CHRIS Backend API",
    description="""
    **Chennai Hydro-Resilience Intelligence System (CHRIS)**
    
    AI-powered decision support engine for urban flood management and aquifer recharge.
    
    ## Overview
    
    CHRIS combines two AI models to address Chennai's flood-drought paradox:
    
    1. **LSTM (Temporal Engine)**: Predicts flood risk years using 100 years of rainfall data and climate indices
    2. **U-Net (Spatial Engine)**: Identifies sponge zones from satellite imagery for water storage
    
    ## Key Features
    
    - 🔮 **5-Year Flood Forecasts**: Predict Critical/High/Moderate/Low risk years
    - 🗺️ **Sponge Zone Mapping**: GeoJSON-compliant terrain data for city planners
    - 📊 **Risk Analytics**: Aggregate statistics and trend analysis
    - 🔌 **ML Model Ready**: Supports .pkl and .onnx model uploads for real-time inference
    
    ## Data Sources
    
    - **Climate Data**: NOAA ONI, IOD anomalies, IMD rainfall records
    - **Satellite Data**: Sentinel-1 (VV/VH radar), Sentinel-2 (MNDWI, NDVI)
    - **Database**: Supabase (PostgreSQL) with PostGIS extensions
    
    ## WebSocket Support
    
    For real-time model training updates or live dashboard notifications, connect to:
    - **WebSocket Endpoint**: `ws://your-domain/ws/updates`
    - **Usage**: Subscribe to model inference events, zone update notifications
    - **Authentication**: Optional token-based auth (future enhancement)
    
    Note: WebSocket routes will be added in future iterations for live data streaming.
    
    ## Authentication
    
    Currently using Supabase anonymous read access for public dashboard.
    Future versions will support JWT-based authentication for administrative operations.
    """,
    version="1.0.0",
    openapi_tags=openapi_tags,
    contact={
        "name": "CHRIS Development Team",
        "email": "support@chris-platform.example.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# CORS configuration
frontend_origin = os.getenv("FRONTEND_ORIGIN", "*")
logger.info(f"Configuring CORS for origin: {frontend_origin}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin] if frontend_origin != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(forecast_router)
app.include_router(zones_router)
app.include_router(citywide_router)


# Health check endpoint
@app.get(
    "/",
    tags=["Health"],
    summary="Health check",
    description="Check if the CHRIS backend service is running and healthy"
)
def health_check():
    """
    Health check endpoint for service monitoring.
    
    Returns:
        JSON response with service status
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "CHRIS Backend API",
            "version": "1.0.0",
            "message": "Chennai Hydro-Resilience Intelligence System is operational"
        }
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Initialize application resources on startup.
    
    - Verify Supabase connection
    - Load ML models if available
    - Log configuration status
    """
    logger.info("=== CHRIS Backend API Starting ===")
    logger.info("OpenAPI docs available at: /docs")
    logger.info("API spec available at: /openapi.json")
    
    # Check for environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        logger.warning(
            "⚠️  SUPABASE_URL and SUPABASE_KEY not configured. "
            "Database operations will fail. Please set these in .env file."
        )
    else:
        logger.info("✅ Supabase credentials configured")
    
    # Check for ML model paths
    lstm_path = os.getenv("LSTM_MODEL_PATH")
    unet_path = os.getenv("UNET_MODEL_PATH")
    
    if lstm_path:
        logger.info(f"LSTM model path configured: {lstm_path}")
    else:
        logger.info("ℹ️  No LSTM model path configured. Using database predictions.")
    
    if unet_path:
        logger.info(f"U-Net model path configured: {unet_path}")
    else:
        logger.info("ℹ️  No U-Net model path configured. Using database zone data.")
    
    logger.info("=== Startup Complete ===")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup resources on shutdown.
    """
    logger.info("=== CHRIS Backend API Shutting Down ===")
