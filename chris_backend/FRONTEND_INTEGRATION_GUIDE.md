# Frontend Integration Guide for CHRIS Backend API

## Quick Start

The CHRIS backend runs on `http://localhost:3001` and provides REST APIs for flood risk prediction and sponge zone mapping.

## Environment Setup

**Backend** runs on port **3001**
**Frontend** should run on port **3000**

### Frontend .env Variables
```bash
REACT_APP_API_BASE=http://localhost:3001/api/v1
REACT_APP_BACKEND_URL=http://localhost:3001
REACT_APP_SUPABASE_URL=https://nzakgyevtibuqbuqapxu.supabase.co
REACT_APP_SUPABASE_KEY=<your_supabase_anon_key>
```

## Available Endpoints

### 1. Health Check (Public)
**GET /health**

```javascript
const response = await axios.get('http://localhost:3001/health');
```

### 2. Citywide Risk Data (Public)
**GET /api/v1/citywide-risk**

Query Parameters:
- `start_year`: Optional (2000-2100)
- `end_year`: Optional (2000-2100)
- `risk_category`: Optional (Low|Moderate|High|Critical)
- `limit`: Default 50, max 1000
- `offset`: Default 0

```javascript
const response = await axios.get('/api/v1/citywide-risk', {
  params: { start_year: 2025, end_year: 2030, limit: 50 }
});
```

### 3. Sponge Zones GeoJSON (Public)
**GET /api/v1/map/sponge-zones**

Query Parameters:
- `capacity_category`: Optional (Low|Moderate|High)
- `terrain_type`: Optional
- `limit`: Default 100, max 500
- `offset`: Default 0

```javascript
const response = await axios.get('/api/v1/map/sponge-zones', {
  params: { capacity_category: 'High', limit: 100 }
});
```

Returns GeoJSON FeatureCollection.

### 4. Zone Details (Public)
**GET /api/v1/map/sponge-zones/{zone_id}/details**

```javascript
const response = await axios.get(`/api/v1/map/sponge-zones/Z001/details`);
```

### 5. Forecast (Protected - JWT Required)
**POST /api/v1/forecast/**

Requires Supabase JWT token in Authorization header.

```javascript
const { data: { session } } = await supabase.auth.getSession();

const response = await axios.post('/api/v1/forecast/', 
  {
    years: 5,
    include_climate_factors: true
  },
  {
    headers: {
      'Authorization': `Bearer ${session.access_token}`
    }
  }
);
```

## Axios Setup with JWT

```javascript
import axios from 'axios';
import { supabase } from './supabaseClient';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE || 'http://localhost:3001/api/v1'
});

// Auto-attach JWT token
api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();
  
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  
  return config;
});

export default api;
```

## Error Handling

- **401**: Invalid/missing JWT token
- **422**: Validation error (invalid parameters)
- **429**: Rate limit exceeded (100 req/60s)
- **500**: Server error

## CORS Configuration

Backend allows:
- `http://localhost:3000`
- `http://localhost:4000`
- Production URLs (configured via ALLOWED_ORIGINS)

## Response Schemas

### Citywide Risk
```typescript
{
  success: boolean;
  data: Array<{
    year: number;
    risk_score: number;
    risk_category: 'Low' | 'Moderate' | 'High' | 'Critical';
    predicted_rainfall_mm: number;
    confidence?: number;
  }>;
  summary: {
    total_years: number;
    highest_risk_year: number;
    highest_risk_score: number;
    average_risk_score: number;
    critical_years: number[];
  };
}
```

### Sponge Zones (GeoJSON)
```typescript
{
  type: 'FeatureCollection';
  features: Array<{
    type: 'Feature';
    id: string;
    geometry: {
      type: 'Polygon';
      coordinates: number[][][];
    };
    properties: {
      zone_id: string;
      zone_name: string;
      capacity_score: number;
      capacity_category: 'Low' | 'Moderate' | 'High';
      recommendation?: string;
    };
  }>;
  metadata: {
    total_zones: number;
    returned_zones: number;
  };
}
```

## Testing Integration

1. Start backend: `cd chris_backend && ./start.sh`
2. Check health: `curl http://localhost:3001/health`
3. Test CORS: Make request from `http://localhost:3000`
4. View API docs: http://localhost:3001/docs

## Performance Notes

- Responses are cached (10-15 min TTL)
- Use pagination for large datasets
- Rate limit: 100 requests per 60 seconds per IP
