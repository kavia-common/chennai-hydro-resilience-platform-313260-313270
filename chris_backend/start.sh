#!/bin/bash
set -e

# Activate virtual environment
source venv/bin/activate

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(grep -v '^#' .env | xargs)
else
    echo "⚠️  Warning: .env file not found. Using default configuration."
fi

# Check for required environment variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
    echo "⚠️  Warning: SUPABASE_URL or SUPABASE_KEY not set."
    echo "   Database operations may fail."
fi

if [ "$SUPABASE_JWT_SECRET" == "REQUIRED_FOR_JWT_VERIFICATION_GET_FROM_SUPABASE_DASHBOARD_SETTINGS_API" ]; then
    echo "⚠️  Warning: SUPABASE_JWT_SECRET is not configured properly."
    echo "   Protected endpoints (like /api/v1/forecast/) will not work."
    echo "   Get JWT secret from: Supabase Dashboard > Project Settings > API > JWT Settings"
fi

# Start uvicorn server
echo ""
echo "Starting CHRIS Backend API..."
echo "  Host: ${UVICORN_HOST:-0.0.0.0}"
echo "  Port: ${PORT:-3001}"
echo "  Environment: ${NODE_ENV:-development}"
echo "  Documentation: http://${UVICORN_HOST:-0.0.0.0}:${PORT:-3001}/docs"
echo "  Health Check: http://${UVICORN_HOST:-0.0.0.0}:${PORT:-3001}/health"
echo "  API Base: http://${UVICORN_HOST:-0.0.0.0}:${PORT:-3001}/api/v1"
echo ""

if [ "${NODE_ENV}" == "production" ]; then
    # Production mode - no reload, multiple workers
    exec uvicorn src.api.main:app \
        --host "${UVICORN_HOST:-0.0.0.0}" \
        --port "${PORT:-3001}" \
        --workers "${UVICORN_WORKERS:-4}" \
        --log-level "${LOG_LEVEL:-info}" \
        --proxy-headers \
        --forwarded-allow-ips='*'
else
    # Development mode - with hot reload
    exec uvicorn src.api.main:app \
        --host "${UVICORN_HOST:-0.0.0.0}" \
        --port "${PORT:-3001}" \
        --reload \
        --log-level "${LOG_LEVEL:-info}" \
        --proxy-headers \
        --forwarded-allow-ips='*'
fi
