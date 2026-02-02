#!/bin/bash
set -e

# Activate virtual environment
source venv/bin/activate

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Start uvicorn server
echo "Starting CHRIS Backend API on port ${PORT:-3001}..."
exec uvicorn src.api.main:app \
    --host "${UVICORN_HOST:-0.0.0.0}" \
    --port "${PORT:-3001}" \
    --reload \
    --log-level info
