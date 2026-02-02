#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="3001"
DEFAULT_LOG_LEVEL="info"
RELOAD_FLAG="--reload"
WORKERS_FLAG=""
PYTHONPATH_DEFAULT="."

# Parse command line arguments
show_help() {
    cat << EOF
${BLUE}CHRIS Backend Start Script${NC}

Usage: ./start.sh [OPTIONS]

Options:
    -h, --help              Show this help message
    -p, --port PORT         Set server port (default: 3001)
    -H, --host HOST         Set server host (default: 0.0.0.0)
    --no-reload             Disable auto-reload (for production)
    --log-level LEVEL       Set log level: debug|info|warning|error (default: info)
    --workers N             Number of worker processes (disables reload)

Examples:
    ./start.sh                          # Start with defaults
    ./start.sh --port 3101              # Start on custom port
    ./start.sh --no-reload              # Disable hot reload
    ./start.sh --log-level debug        # Enable debug logging
    ./start.sh --workers 4              # Production mode with 4 workers

Access:
    - Local: http://localhost:PORT
    - Proxy: /proxy/PORT/ (in development environment)
    - API Docs: http://localhost:PORT/docs
    - Health: http://localhost:PORT/health

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -p|--port)
            CUSTOM_PORT="$2"
            shift 2
            ;;
        -H|--host)
            CUSTOM_HOST="$2"
            shift 2
            ;;
        --no-reload)
            RELOAD_FLAG=""
            shift
            ;;
        --log-level)
            CUSTOM_LOG_LEVEL="$2"
            shift 2
            ;;
        --workers)
            WORKERS_FLAG="--workers $2"
            RELOAD_FLAG=""  # Disable reload when using workers
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Load .env file if present
if [ -f .env ]; then
    echo -e "${GREEN}✓${NC} Loading environment variables from .env..."
    # Export variables from .env (skip comments and empty lines)
    set -a
    source <(grep -v '^#' .env | grep -v '^[[:space:]]*$' | sed 's/\r$//')
    set +a
else
    echo -e "${YELLOW}⚠${NC}  .env file not found. Using defaults..."
fi

# Apply defaults if not set
export PYTHONPATH="${PYTHONPATH:-$PYTHONPATH_DEFAULT}"
export UVICORN_HOST="${CUSTOM_HOST:-${UVICORN_HOST:-$DEFAULT_HOST}}"
export UVICORN_PORT="${CUSTOM_PORT:-${PORT:-$DEFAULT_PORT}}"
export LOG_LEVEL="${CUSTOM_LOG_LEVEL:-${LOG_LEVEL:-$DEFAULT_LOG_LEVEL}}"

# Ensure ALLOWED_ORIGINS includes localhost:3000
if [ -z "$ALLOWED_ORIGINS" ]; then
    export ALLOWED_ORIGINS="http://localhost:3000,http://localhost:3001,http://localhost:4000"
else
    # Add localhost:3000 if not already present
    if [[ ! "$ALLOWED_ORIGINS" =~ "localhost:3000" ]]; then
        export ALLOWED_ORIGINS="http://localhost:3000,$ALLOWED_ORIGINS"
    fi
fi

# Validation checks
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  CHRIS Backend API Server${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo -e "  Host:         ${UVICORN_HOST}"
echo -e "  Port:         ${UVICORN_PORT}"
echo -e "  Log Level:    ${LOG_LEVEL}"
echo -e "  Python Path:  ${PYTHONPATH}"
echo -e "  Reload:       $([ -n "$RELOAD_FLAG" ] && echo 'Enabled' || echo 'Disabled')"
echo -e "  Workers:      $([ -n "$WORKERS_FLAG" ] && echo "${WORKERS_FLAG#--workers }" || echo '1 (dev mode)')"
echo -e "  Environment:  ${NODE_ENV:-development}"
echo ""

# Check environment variables
warnings=0

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
    echo -e "${YELLOW}⚠${NC}  Warning: SUPABASE_URL or SUPABASE_KEY not set."
    echo -e "   Database operations may fail."
    ((warnings++))
fi

if [ "$SUPABASE_JWT_SECRET" == "your_supabase_jwt_secret_from_dashboard" ] || \
   [ "$SUPABASE_JWT_SECRET" == "REQUIRED_FOR_JWT_VERIFICATION_GET_FROM_SUPABASE_DASHBOARD_SETTINGS_API" ] || \
   [ -z "$SUPABASE_JWT_SECRET" ]; then
    echo -e "${YELLOW}⚠${NC}  Warning: SUPABASE_JWT_SECRET not configured."
    echo -e "   Protected endpoints (e.g., /api/v1/forecast/) will not work."
    echo -e "   Get JWT secret from: Supabase Dashboard > Settings > API > JWT Settings"
    ((warnings++))
fi

if [ $warnings -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠  $warnings warning(s) detected. Server will start but some features may not work.${NC}"
fi

echo ""
echo -e "${GREEN}Access URLs:${NC}"
echo -e "  API Docs:     http://localhost:${UVICORN_PORT}/docs"
echo -e "  Health:       http://localhost:${UVICORN_PORT}/health"
echo -e "  OpenAPI:      http://localhost:${UVICORN_PORT}/openapi.json"
echo -e "  Proxy:        /proxy/${UVICORN_PORT}/ (in dev environment)"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}Starting server...${NC}"
echo ""

# Build uvicorn command
CMD="uvicorn src.api.main:app --host $UVICORN_HOST --port $UVICORN_PORT $RELOAD_FLAG --log-level $LOG_LEVEL $WORKERS_FLAG"

# Start server with error handling
if ! $CMD; then
    EXIT_CODE=$?
    echo ""
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}  Server failed to start (exit code: $EXIT_CODE)${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo ""
    echo -e "  1. ${BLUE}Port already in use?${NC}"
    echo -e "     Check: lsof -i :${UVICORN_PORT}"
    echo -e "     Kill:  kill -9 \$(lsof -t -i:${UVICORN_PORT})"
    echo ""
    echo -e "  2. ${BLUE}Missing dependencies?${NC}"
    echo -e "     Run: pip install -r requirements.txt"
    echo ""
    echo -e "  3. ${BLUE}Import errors?${NC}"
    echo -e "     Verify PYTHONPATH is set correctly"
    echo -e "     Current: $PYTHONPATH"
    echo ""
    echo -e "  4. ${BLUE}Environment issues?${NC}"
    echo -e "     Check .env file exists and has valid values"
    echo -e "     Compare with .env.example"
    echo ""
    echo -e "  5. ${BLUE}Module not found?${NC}"
    echo -e "     Ensure you're in the correct directory"
    echo -e "     Path: chennai-hydro-resilience-platform-313260-313270/chris_backend"
    echo ""
    echo -e "For detailed logs, try: ${BLUE}./start.sh --log-level debug${NC}"
    echo ""
    exit $EXIT_CODE
fi
