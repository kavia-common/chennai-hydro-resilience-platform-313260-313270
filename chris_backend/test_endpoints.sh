#!/bin/bash

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BASE_URL="${BACKEND_URL:-http://localhost:3001}"
TIMEOUT=5

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  CHRIS Backend Endpoint Tests${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "Testing backend at: ${BLUE}${BASE_URL}${NC}"
echo ""

# Function to test endpoint
test_endpoint() {
    local method=$1
    local path=$2
    local description=$3
    local data=$4
    
    echo -n "Testing ${method} ${path} ... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" --connect-timeout $TIMEOUT "${BASE_URL}${path}" 2>/dev/null)
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" --connect-timeout $TIMEOUT \
            -X POST \
            -H "Content-Type: application/json" \
            -d "$data" \
            "${BASE_URL}${path}" 2>/dev/null)
    fi
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ -z "$http_code" ]; then
        echo -e "${RED}✗ FAILED (No response)${NC}"
        return 1
    fi
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "${GREEN}✓ PASSED (${http_code})${NC}"
        return 0
    elif [ "$http_code" -eq 401 ] || [ "$http_code" -eq 403 ]; then
        echo -e "${YELLOW}⚠ AUTH REQUIRED (${http_code})${NC}"
        return 0
    elif [ "$http_code" -eq 404 ]; then
        echo -e "${YELLOW}⚠ NOT FOUND (${http_code})${NC} - Check if data exists"
        return 0
    else
        echo -e "${RED}✗ FAILED (${http_code})${NC}"
        return 1
    fi
}

# Wait for backend to be ready
echo -e "${YELLOW}Waiting for backend to be ready...${NC}"
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -s --connect-timeout 2 "${BASE_URL}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is ready!${NC}"
        echo ""
        break
    fi
    attempt=$((attempt + 1))
    sleep 1
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}✗ Backend did not start within ${max_attempts} seconds${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo "  1. Check if backend is running: ps aux | grep uvicorn"
    echo "  2. Check logs: tail -f /tmp/chris_backend.log"
    echo "  3. Try starting manually: ./start.sh"
    echo ""
    exit 1
fi

# Run tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Public Endpoints (No Auth Required)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

passed=0
failed=0

# Health check
if test_endpoint "GET" "/health" "Health check"; then
    ((passed++))
else
    ((failed++))
fi

# Root endpoint
if test_endpoint "GET" "/" "Root endpoint"; then
    ((passed++))
else
    ((failed++))
fi

# Citywide risk
if test_endpoint "GET" "/api/v1/citywide-risk" "Citywide risk data"; then
    ((passed++))
else
    ((failed++))
fi

# Sponge zones
if test_endpoint "GET" "/api/v1/map/sponge-zones" "Sponge zones"; then
    ((passed++))
else
    ((failed++))
fi

# Sponge zone details (might 404 if no data)
if test_endpoint "GET" "/api/v1/map/sponge-zones/Z001/details" "Zone details"; then
    ((passed++))
else
    ((failed++))
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Protected Endpoints (Auth Required)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Forecast (should return 401 without JWT)
if test_endpoint "POST" "/api/v1/forecast/" "Forecast generation" '{"years": 5, "include_climate_factors": true}'; then
    ((passed++))
else
    ((failed++))
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  API Documentation${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# OpenAPI docs
if test_endpoint "GET" "/docs" "Swagger UI"; then
    ((passed++))
else
    ((failed++))
fi

# OpenAPI JSON
if test_endpoint "GET" "/openapi.json" "OpenAPI spec"; then
    ((passed++))
else
    ((failed++))
fi

# Summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Test Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Passed:  ${GREEN}${passed}${NC}"
echo -e "  Failed:  ${RED}${failed}${NC}"
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✓ All endpoint tests passed!${NC}"
    echo ""
    echo -e "${BLUE}Access URLs:${NC}"
    echo -e "  API Docs:     ${BASE_URL}/docs"
    echo -e "  Health:       ${BASE_URL}/health"
    echo -e "  OpenAPI:      ${BASE_URL}/openapi.json"
    echo ""
    exit 0
else
    echo -e "${YELLOW}⚠ Some tests failed. Check the output above.${NC}"
    echo ""
    exit 1
fi
