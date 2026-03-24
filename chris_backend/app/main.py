from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.http import add_exception_handlers, add_request_id_middleware, parse_cors_origins
from app.core.settings import settings
from app.routers import health, model_info, predict

app = FastAPI(
    title="CHRIS Backend API",
    version="0.2.0",
    description="CHRIS (Chennai Hydro-Resilience Intelligence System) backend APIs for ML inference.",
)

# Request-id middleware for traceability (adds X-Request-Id and request.state.request_id)
add_request_id_middleware(app)

# Consistent error envelope across all exceptions (ApiError, validation, HTTPException, etc.)
add_exception_handlers(app)

# Configurable CORS for React app integration
cors_origins = parse_cors_origins(raw=settings.chris_cors_allow_origins, fallback_origin=settings.react_app_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=bool(settings.chris_cors_allow_credentials),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(model_info.router)
app.include_router(predict.router)
