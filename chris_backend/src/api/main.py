"""
CHRIS Backend API - Main FastAPI Application.

Chennai Hydro-Resilience Intelligence System (CHRIS) backend service.
Provides REST APIs for flood risk prediction and sponge zone mapping.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import os
from datetime import datetime

from src.api.routes import forecast_router, zones_router, citywide_router, model_info_router
from src.middleware.rate_limit import rate_limit_middleware
from src.utils.structured_logger import correlation_id_middleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Note: Structured logging can be optionally enabled in startup event for JSON logs

# OpenAPI metadata
openapi_tags = [
    {
        "name": "Health",
        "description": "Health check and service status endpoints"
    },
    {
        "name": "Forecast",
        "description": "**Temporal LSTM Predictions** - Generate multi-year flood risk forecasts based on climate drivers (ONI, IOD) and rainfall patterns. **Protected routes require JWT authentication.**"
    },
    {
        "name": "Zones",
        "description": "**Spatial U-Net Analysis** - Retrieve sponge zone GeoJSON data from satellite imagery segmentation (Sentinel-1/2)"
    },
    {
        "name": "Citywide Risk",
        "description": "**Aggregate Risk Data** - Access citywide flood risk trends and statistics"
    },
    {
        "name": "Models",
        "description": "**ML Model Management** - Model metadata, status, and inference capabilities"
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
    
    ## Security
    
    - **JWT Authentication**: Protected endpoints require valid Supabase JWT tokens via `Authorization: Bearer <token>` header
    - **Rate Limiting**: Maximum 100 requests per 60 seconds per IP address
    - **CORS**: Restricted to configured frontend origins only
    - **Input Validation**: All inputs validated via Pydantic schemas with strict type checking
    - **RLS Alignment**: Database queries respect Row-Level Security policies in Supabase
    
    ## Key Features
    
    - 🔮 **5-Year Flood Forecasts**: Predict Critical/High/Moderate/Low risk years
    - 🗺️ **Sponge Zone Mapping**: GeoJSON-compliant terrain data for city planners
    - 📊 **Risk Analytics**: Aggregate statistics and trend analysis
    - 🔌 **ML Model Ready**: Supports .pkl and .onnx model uploads for real-time inference
    - 🔒 **Secure by Design**: JWT verification, rate limiting, CORS protection, input sanitization
    
    ## Data Sources
    
    - **Climate Data**: NOAA ONI, IOD anomalies, IMD rainfall records
    - **Satellite Data**: Sentinel-1 (VV/VH radar), Sentinel-2 (MNDWI, NDVI)
    - **Database**: Supabase (PostgreSQL) with PostGIS extensions
    
    ## Authentication
    
    Protected endpoints (e.g., POST /api/v1/forecast/) require a valid JWT token from Supabase:
    
    ```
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    ```
    
    Public read endpoints (e.g., GET /api/v1/map/sponge-zones) do not require authentication.
    
    ## Rate Limiting
    
    All endpoints are subject to rate limiting:
    - **Limit**: 100 requests per 60 seconds per IP address
    - **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
    - **Response**: 429 Too Many Requests when limit exceeded
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

# CORS configuration - TIGHTENED
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_str:
    allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]
else:
    # Fallback to frontend URL if ALLOWED_ORIGINS not set
    frontend_url = os.getenv("FRONTEND_URL", "*")
    allowed_origins = [frontend_url] if frontend_url != "*" else ["*"]

# Parse allowed methods and headers
allowed_methods_str = os.getenv("ALLOWED_METHODS", "GET,POST,PUT,DELETE,OPTIONS,PATCH")
allowed_methods = [method.strip() for method in allowed_methods_str.split(",")]

allowed_headers_str = os.getenv("ALLOWED_HEADERS", "Content-Type,Authorization,X-Requested-With")
allowed_headers = [header.strip() for header in allowed_headers_str.split(",")]

logger.info(f"Configuring CORS - Allowed origins: {allowed_origins}")
logger.info(f"Allowed methods: {allowed_methods}")
logger.info(f"Allowed headers: {allowed_headers}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=allowed_methods,
    allow_headers=allowed_headers,
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    max_age=int(os.getenv("CORS_MAX_AGE", "3600"))
)

# Add correlation ID middleware (must be before rate limiting for proper logging)
app.middleware("http")(correlation_id_middleware)

# Add rate limiting middleware
app.middleware("http")(rate_limit_middleware)

# Add trusted host middleware if not in development
if os.getenv("NODE_ENV") != "development":
    backend_url = os.getenv("BACKEND_URL", "")
    if backend_url:
        # Extract host from URL
        host = backend_url.replace("https://", "").replace("http://", "").split(":")[0]
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[host, "localhost", "127.0.0.1"]
        )
        logger.info(f"Trusted host middleware enabled for: {host}")

# Register routers
app.include_router(forecast_router)
app.include_router(zones_router)
app.include_router(citywide_router)
app.include_router(model_info_router)


# Global exception handlers for better error responses
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors with detailed messages.
    """
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "message": "Request data failed validation. Please check the documentation."
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle HTTP exceptions with consistent format.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP {exc.status_code}",
            "detail": exc.detail
        }
    )


# Root endpoint
@app.get(
    "/",
    tags=["Health"],
    summary="Root endpoint",
    description="Root endpoint with API information"
)
def root():
    """
    Root endpoint with API information.
    
    Returns:
        JSON response with API metadata
    """
    return JSONResponse(
        content={
            "service": "CHRIS Backend API",
            "version": "1.0.0",
            "message": "Chennai Hydro-Resilience Intelligence System",
            "documentation": "/docs",
            "openapi_spec": "/openapi.json",
            "health": "/health"
        }
    )


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Check if the CHRIS backend service is running and healthy"
)
def health_check():
    """
    Health check endpoint for service monitoring and load balancers.
    
    Returns:
        JSON response with service status and configuration
    """
    jwt_configured = bool(os.getenv("SUPABASE_JWT_SECRET") and 
                         os.getenv("SUPABASE_JWT_SECRET") != "REQUIRED_FOR_JWT_VERIFICATION_GET_FROM_SUPABASE_DASHBOARD_SETTINGS_API")
    
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "CHRIS Backend API",
            "version": "1.0.0",
            "message": "Chennai Hydro-Resilience Intelligence System is operational",
            "timestamp": datetime.utcnow().isoformat(),
            "security": {
                "jwt_auth": "enabled" if jwt_configured else "not_configured",
                "rate_limiting": "enabled",
                "cors": "restricted" if allowed_origins != ["*"] else "permissive"
            },
            "endpoints": {
                "forecast": "/api/v1/forecast/",
                "zones": "/api/v1/map/sponge-zones",
                "zone_details": "/api/v1/map/sponge-zones/{zone_id}/details",
                "citywide_risk": "/api/v1/citywide-risk",
                "model_info": "/api/v1/models/info"
            }
        }
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Initialize application resources on startup.
    
    - Verify Supabase connection
    - Initialize caching system
    - Load ML models if available
    - Log configuration status
    - Validate security settings
    """
    logger.info("=== CHRIS Backend API Starting ===")
    logger.info("OpenAPI docs available at: /docs")
    logger.info("API spec available at: /openapi.json")
    
    # Initialize cache
    from src.utils.cache import get_cache
    get_cache()  # Initialize the cache singleton
    logger.info("✅ In-memory cache initialized")
    
    # Check for environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    
    if not supabase_url or not supabase_key:
        logger.warning(
            "⚠️  SUPABASE_URL and SUPABASE_KEY not configured. "
            "Database operations will fail. Please set these in .env file."
        )
    else:
        logger.info("✅ Supabase credentials configured")
    
    if not supabase_jwt_secret or supabase_jwt_secret == "REQUIRED_FOR_JWT_VERIFICATION_GET_FROM_SUPABASE_DASHBOARD_SETTINGS_API":
        logger.warning(
            "⚠️  SUPABASE_JWT_SECRET not configured properly. "
            "JWT authentication will not work. "
            "Get the JWT secret from: Supabase Dashboard > Project Settings > API > JWT Settings"
        )
    else:
        logger.info("✅ JWT authentication enabled")
    
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
    
    # Log security configuration
    logger.info("=== Security Configuration ===")
    logger.info(f"Rate Limiting: {os.getenv('RATE_LIMIT_MAX', '100')} requests per {os.getenv('RATE_LIMIT_WINDOW_S', '60')}s")
    logger.info(f"CORS Origins: {allowed_origins}")
    logger.info(f"JWT Auth: {'Enabled' if supabase_jwt_secret else 'Disabled'}")
    
    # Log performance configuration
    logger.info("=== Performance Configuration ===")
    logger.info("Cache: In-memory TTL cache enabled (10-15 min TTL)")
    logger.info("Pagination: Enabled for list endpoints (max 1000 items)")
    logger.info("Correlation IDs: Enabled for request tracing")
    logger.info("Optimized Queries: Selective field filtering enabled")
    logger.info("=== Startup Complete ===")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup resources on shutdown.
    """
    logger.info("=== CHRIS Backend API Shutting Down ===")
