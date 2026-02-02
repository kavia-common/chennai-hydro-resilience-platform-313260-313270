# CHRIS Backend API - Endpoint Reference

## Base URL
- **Development**: `http://localhost:3001`
- **Production**: Set via `BACKEND_URL` environment variable

## Core Endpoints

### Health & Status

#### GET `/`
Root endpoint with API information.

**Response:**
```json
{
  "service": "CHRIS Backend API",
  "version": "1.0.0",
  "message": "Chennai Hydro-Resilience Intelligence System",
  "documentation": "/docs",
  "openapi_spec": "/openapi.json",
  "health": "/health"
}
```

#### GET `/health`
Health check endpoint for monitoring and load balancers.

**Response:**
```json
{
  "status": "healthy",
  "service": "CHRIS Backend API",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "security": {
    "jwt_auth": "enabled",
    "rate_limiting": "enabled",
    "cors": "restricted"
  },
  "endpoints": {
    "forecast": "/api/v1/forecast/",
    "zones": "/api/v1/map/sponge-zones",
    "zone_details": "/api/v1/map/sponge-zones/{zone_id}/details",
    "citywide_risk": "/api/v1/citywide-risk"
  }
}
```

### Map & Zones

#### GET `/api/v1/map/sponge-zones`
Retrieve sponge zones as GeoJSON FeatureCollection with pagination and caching.

**Query Parameters:**
- `capacity_category` (optional): Filter by `Low`, `Moderate`, or `High`
- `terrain_type` (optional): Filter by terrain classification
- `limit` (optional): Items per page (1-500, default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response:** GeoJSON FeatureCollection
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "Z001",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[80.27, 13.00], [80.28, 13.00]]]
      },
      "properties": {
        "zone_id": "Z001",
        "zone_name": "Adyar River Basin",
        "capacity_score": 85.2,
        "capacity_category": "High",
        "terrain_type": "Wetland",
        "recommendation": "Ideal for rainwater harvesting"
      }
    }
  ],
  "metadata": {
    "total_zones": 5,
    "returned_zones": 1
  }
}
```

#### GET `/api/v1/map/sponge-zones/{zone_id}/details`
Get detailed information for a specific sponge zone.

**Path Parameters:**
- `zone_id` (required): Zone identifier (e.g., 'Z001')

**Response:**
```json
{
  "success": true,
  "data": {
    "type": "Feature",
    "id": "Z001",
    "geometry": { ... },
    "properties": {
      "zone_id": "Z001",
      "zone_name": "Adyar River Basin",
      "capacity_score": 85.2,
      "capacity_category": "High",
      "vv_amplitude": -12.5,
      "vh_backscatter": -18.3,
      "mndwi": 0.45,
      "ndvi": 0.62,
      "terrain_type": "Wetland",
      "recommendation": "Ideal for rainwater harvesting and aquifer recharge"
    }
  }
}
```

### Citywide Risk

#### GET `/api/v1/citywide-risk`
Get aggregate citywide flood risk statistics and trends.

**Query Parameters:**
- `limit` (optional): Items per page (default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "year": 2024,
      "risk_level": "High",
      "risk_score": 78.5,
      "affected_zones": 12,
      "recommendation": "Enhanced preparedness measures recommended"
    }
  ],
  "metadata": {
    "total_records": 10,
    "returned_records": 10
  }
}
```

### Forecast (Protected)

#### POST `/api/v1/forecast/`
Generate flood risk forecast based on climate data.

**Authentication Required:** JWT token via `Authorization: Bearer <token>` header

**Request Body:**
```json
{
  "oni_anomaly": 1.5,
  "iod_anomaly": 0.8,
  "rainfall_mm": 1200.5
}
```

**Response:**
```json
{
  "success": true,
  "prediction": {
    "risk_category": "High",
    "risk_score": 0.85,
    "confidence": 0.92,
    "factors": {
      "oni_contribution": 0.35,
      "iod_contribution": 0.25,
      "rainfall_contribution": 0.40
    }
  },
  "model_version": "v1.0-lstm"
}
```

## CORS Configuration

The backend is configured to accept requests from:
- `http://localhost:3000` (frontend development)
- `http://localhost:3001` (backend direct access)
- Proxy paths configured in ALLOWED_ORIGINS

## Rate Limiting

- **Limit**: 100 requests per 60 seconds per IP
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **Response**: 429 Too Many Requests when exceeded

## Security

- **CORS**: Restricted to configured origins only
- **JWT Authentication**: Required for protected endpoints (forecast)
- **Input Validation**: All inputs validated via Pydantic schemas
- **Rate Limiting**: Prevents abuse and DoS attacks

## Frontend Integration

The frontend should use these endpoints with the base URL set via environment variable:
- Development: `http://localhost:3001`
- Production: Set via `REACT_APP_API_BASE_URL` or similar

Example frontend fetch:
```javascript
const response = await fetch('http://localhost:3001/api/v1/map/sponge-zones');
const data = await response.json();
```

## Testing

Run the verification script to test all endpoints:
```bash
cd chris_backend
python3 verify_backend.py
```

## Documentation

- **Interactive API Docs**: http://localhost:3001/docs
- **OpenAPI Spec**: http://localhost:3001/openapi.json
- **Health Check**: http://localhost:3001/health
```
