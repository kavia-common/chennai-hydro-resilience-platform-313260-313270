# CHRIS Backend - Startup and Testing Guide

## Quick Start

### 1. Verify Configuration

Before starting the backend, verify everything is properly configured:

```bash
python3 verify_startup.py
```

This will check:
- ✅ Environment variables (.env file)
- ✅ Python dependencies
- ✅ Source code structure
- ✅ Import paths
- ✅ Route registration

### 2. Start the Backend

**Option A: Using the start script (recommended)**
```bash
./start.sh
```

**Option B: Custom port**
```bash
./start.sh --port 3001
```

**Option C: Production mode (no reload, multiple workers)**
```bash
./start.sh --no-reload --workers 4
```

**Option D: Manual start**
```bash
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload
```

### 3. Test Endpoints

Once the backend is running, test all endpoints:

```bash
./test_endpoints.sh
```

Or test manually with curl:

```bash
# Health check
curl http://localhost:3001/health

# Citywide risk data (public)
curl http://localhost:3001/api/v1/citywide-risk

# Sponge zones (public)
curl http://localhost:3001/api/v1/map/sponge-zones

# Zone details (public)
curl http://localhost:3001/api/v1/map/sponge-zones/Z001/details

# Forecast (protected - requires JWT)
curl -X POST http://localhost:3001/api/v1/forecast/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"years": 5, "include_climate_factors": true}'
```

## Available Endpoints

### Public Endpoints (No Authentication)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root endpoint with API info |
| GET | `/health` | Health check endpoint |
| GET | `/docs` | Swagger UI documentation |
| GET | `/openapi.json` | OpenAPI specification |
| GET | `/api/v1/citywide-risk` | Citywide flood risk data |
| GET | `/api/v1/map/sponge-zones` | GeoJSON sponge zones |
| GET | `/api/v1/map/sponge-zones/{zone_id}/details` | Specific zone details |

### Protected Endpoints (JWT Required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/forecast/` | Generate flood risk forecast |

## Frontend Integration

The backend is configured to accept requests from the frontend:

**CORS Configuration:**
- Allowed origins: Set in `.env` via `ALLOWED_ORIGINS`
- Allowed methods: GET, POST, PUT, DELETE, PATCH, OPTIONS
- Allowed headers: Content-Type, Authorization, X-Requested-With
- Credentials: Enabled

**Frontend API Base URL:**
```javascript
// In your React frontend
const API_BASE = process.env.REACT_APP_BACKEND_URL || 'http://localhost:3001';

// Example API calls
const response = await fetch(`${API_BASE}/api/v1/citywide-risk`);
const data = await response.json();
```

## Environment Variables

Key environment variables in `.env`:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_JWT_SECRET=your_jwt_secret

# Backend URLs
BACKEND_URL=https://your-domain:3001
FRONTEND_URL=https://your-domain:3000

# CORS
ALLOWED_ORIGINS=https://your-domain:3000,http://localhost:3000

# Server
PORT=3001
HOST=0.0.0.0
NODE_ENV=development

# Rate Limiting
RATE_LIMIT_MAX=100
RATE_LIMIT_WINDOW_S=60
```

## Troubleshooting

### Backend won't start

1. **Port already in use:**
   ```bash
   lsof -i :3001
   kill -9 $(lsof -t -i:3001)
   ```

2. **Missing dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Import errors:**
   ```bash
   export PYTHONPATH=.
   python3 verify_startup.py
   ```

### Endpoints return errors

1. **401 Unauthorized on protected endpoints:**
   - Expected! POST `/api/v1/forecast/` requires JWT token
   - Get token from Supabase auth in frontend
   - Pass in `Authorization: Bearer <token>` header

2. **404 Not Found on data endpoints:**
   - Database might be empty
   - Check Supabase tables: `citywide_risk`, `zone_risk`
   - Populate with sample data or wait for ML model integration

3. **500 Internal Server Error:**
   - Check logs for details
   - Verify Supabase credentials in `.env`
   - Test Supabase connection

### CORS errors from frontend

1. **Check ALLOWED_ORIGINS in .env:**
   ```bash
   ALLOWED_ORIGINS=https://your-frontend-domain:3000,http://localhost:3000
   ```

2. **Verify frontend URL matches:**
   - Frontend must use exact URL in ALLOWED_ORIGINS
   - Include protocol (http/https) and port

3. **Check browser console:**
   - Look for CORS preflight (OPTIONS) request
   - Verify response headers include Access-Control-Allow-Origin

## Testing with Frontend

### Method 1: Run both locally

**Terminal 1 - Backend:**
```bash
cd chris_backend
./start.sh
```

**Terminal 2 - Frontend:**
```bash
cd chris_frontend
npm start
```

**Terminal 3 - Test:**
```bash
# From frontend, API calls should work
# Open browser: http://localhost:3000
# Check browser DevTools Network tab
```

### Method 2: Test API directly

```bash
# Test health
curl http://localhost:3001/health | jq

# Test citywide risk with pretty print
curl http://localhost:3001/api/v1/citywide-risk?limit=10 | jq

# Test sponge zones
curl http://localhost:3001/api/v1/map/sponge-zones | jq
```

## Performance & Monitoring

### Check cache effectiveness

Endpoints use caching to reduce database load:
- `/api/v1/map/sponge-zones`: 10 min cache
- `/api/v1/map/sponge-zones/{id}/details`: 15 min cache
- `/api/v1/citywide-risk`: 10 min cache

**Test cache:**
```bash
# First call - hits database
time curl -s http://localhost:3001/api/v1/citywide-risk > /dev/null

# Second call - from cache (should be faster)
time curl -s http://localhost:3001/api/v1/citywide-risk > /dev/null
```

### Check rate limiting

Rate limit: 100 requests per 60 seconds per IP

```bash
# Test rate limit headers
curl -I http://localhost:3001/health

# Look for:
# X-RateLimit-Limit: 100
# X-RateLimit-Remaining: 99
# X-RateLimit-Reset: <timestamp>
```

## Database Setup

The backend expects these Supabase tables:

### citywide_risk table
```sql
CREATE TABLE citywide_risk (
  year INT PRIMARY KEY,
  risk_score FLOAT,
  risk_category TEXT,
  predicted_rainfall_mm FLOAT,
  oni_anomaly FLOAT,
  iod_anomaly FLOAT,
  confidence FLOAT
);
```

### zone_risk table
```sql
CREATE TABLE zone_risk (
  zone_id TEXT PRIMARY KEY,
  zone_name TEXT,
  capacity_score FLOAT,
  capacity_category TEXT,
  geometry JSONB,
  vv_amplitude FLOAT,
  vh_backscatter FLOAT,
  mndwi FLOAT,
  ndvi FLOAT,
  terrain_type TEXT,
  recommendation TEXT
);
```

## Next Steps

1. ✅ Backend is configured and ready
2. ✅ All routes are implemented
3. ✅ Health check is available at `/health`
4. ✅ CORS is configured for frontend
5. 🔄 Populate database with sample data (if needed)
6. 🔄 Test integration with frontend
7. 🔄 Upload ML models for real-time inference (optional)

## Support

- **API Documentation:** http://localhost:3001/docs
- **OpenAPI Spec:** http://localhost:3001/openapi.json
- **Health Check:** http://localhost:3001/health

For issues, check:
1. Backend logs (console output)
2. Browser DevTools console (for frontend issues)
3. Network tab (for API calls)
4. Supabase dashboard (for database issues)
