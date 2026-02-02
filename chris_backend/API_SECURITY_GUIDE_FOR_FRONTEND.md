# CHRIS Backend API - Security Guide for Frontend Developers

## Quick Reference

This guide explains how to interact with the secured CHRIS Backend API from the frontend application.

---

## 🔑 Authentication

### Protected Endpoints

Only one endpoint currently requires authentication:

- **`POST /api/v1/forecast/`** - Generate flood risk forecasts

### Public Endpoints (No Auth Required)

- `GET /` - Health check
- `GET /api/v1/map/sponge-zones` - Sponge zones GeoJSON
- `GET /api/v1/zone-details` - Zone details
- `GET /api/v1/citywide-risk` - Citywide risk data

### How to Send JWT Tokens

**With Fetch API:**
```javascript
const response = await fetch('http://localhost:3001/api/v1/forecast/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${userJwtToken}`
  },
  body: JSON.stringify({
    years: 5,
    include_climate_factors: true
  })
});
```

**With Axios:**
```javascript
const response = await axios.post(
  'http://localhost:3001/api/v1/forecast/',
  {
    years: 5,
    include_climate_factors: true
  },
  {
    headers: {
      'Authorization': `Bearer ${userJwtToken}`
    }
  }
);
```

**With Supabase Client:**
```javascript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.REACT_APP_SUPABASE_URL,
  process.env.REACT_APP_SUPABASE_ANON_KEY
);

// Get session token
const { data: { session } } = await supabase.auth.getSession();
const jwtToken = session?.access_token;

// Use token in API request
const response = await fetch('http://localhost:3001/api/v1/forecast/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${jwtToken}`
  },
  body: JSON.stringify({ years: 5 })
});
```

---

## 🚦 Rate Limiting

### Limits

- **Global Limit:** 100 requests per 60 seconds per IP address
- Applies to ALL endpoints

### Rate Limit Headers

Every response includes rate limit information:

```javascript
const response = await fetch('http://localhost:3001/api/v1/citywide-risk');

const limit = response.headers.get('X-RateLimit-Limit');        // "100"
const remaining = response.headers.get('X-RateLimit-Remaining'); // "95"
const reset = response.headers.get('X-RateLimit-Reset');        // "1738488120"
```

### Handling Rate Limit Errors

**HTTP 429 - Too Many Requests:**

```javascript
try {
  const response = await fetch('http://localhost:3001/api/v1/citywide-risk');
  
  if (response.status === 429) {
    const data = await response.json();
    const retryAfter = response.headers.get('Retry-After'); // seconds
    
    console.error(`Rate limited. Retry after ${retryAfter} seconds`);
    
    // Show user-friendly message
    showNotification(`Please wait ${retryAfter} seconds before trying again.`);
    
    // Optional: Retry after delay
    setTimeout(() => {
      // Retry request
    }, retryAfter * 1000);
  }
} catch (error) {
  console.error('Request failed:', error);
}
```

### Best Practices

1. **Cache responses** when possible
2. **Debounce** user inputs (e.g., search, filters)
3. **Display rate limit info** to users
4. **Handle 429 errors** gracefully with retry logic

**Example: Debounced Search**
```javascript
import { debounce } from 'lodash';

const debouncedSearch = debounce(async (searchTerm) => {
  const response = await fetch(
    `http://localhost:3001/api/v1/zone-details?zone_id=${searchTerm}`
  );
  const data = await response.json();
  // Update UI
}, 500); // Wait 500ms after user stops typing
```

---

## ✅ Input Validation

### Request Validation

The backend performs strict validation. Invalid inputs return **HTTP 422 Unprocessable Entity**.

### Forecast Request Validation

```javascript
// ✅ Valid request
{
  "years": 5,                      // Must be 1-10
  "include_climate_factors": true  // Boolean
}

// ❌ Invalid request (years out of range)
{
  "years": 15,  // ERROR: Must be between 1 and 10
  "include_climate_factors": true
}

// ❌ Invalid request (wrong type)
{
  "years": "five",  // ERROR: Must be integer
  "include_climate_factors": "yes"  // ERROR: Must be boolean
}
```

### Query Parameter Validation

**Citywide Risk Filters:**
```javascript
// ✅ Valid
const url = new URL('http://localhost:3001/api/v1/citywide-risk');
url.searchParams.append('start_year', '2025');  // 2000-2100
url.searchParams.append('end_year', '2030');    // 2000-2100
url.searchParams.append('risk_category', 'High'); // Low|Moderate|High|Critical

// ❌ Invalid
url.searchParams.append('risk_category', 'SuperHigh'); // ERROR: Invalid category
url.searchParams.append('start_year', '2030');
url.searchParams.append('end_year', '2025');  // ERROR: start > end
```

**Sponge Zone Filters:**
```javascript
// ✅ Valid
const url = new URL('http://localhost:3001/api/v1/map/sponge-zones');
url.searchParams.append('capacity_category', 'High'); // Low|Moderate|High
url.searchParams.append('terrain_type', 'Wetland');

// ❌ Invalid
url.searchParams.append('capacity_category', 'VeryHigh'); // ERROR: Invalid category
```

**Zone Details:**
```javascript
// ✅ Valid zone IDs
const zoneIds = ['Z001', 'Z002', 'ZONE_123', 'zone-abc'];

// ❌ Invalid zone IDs (will be rejected)
const invalidIds = [
  "Z001'; DROP TABLE zone_risk;--",  // SQL injection attempt
  "Z001<script>alert(1)</script>",    // XSS attempt
  "Z001 OR 1=1",                      // SQL injection
  "../../etc/passwd"                   // Path traversal
];
```

### Handling Validation Errors

```javascript
try {
  const response = await fetch('http://localhost:3001/api/v1/forecast/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      years: 15  // Invalid: exceeds max of 10
    })
  });
  
  if (response.status === 422) {
    const errorData = await response.json();
    
    // Structure: { error, detail: [...] }
    console.error('Validation errors:', errorData.detail);
    
    // Display user-friendly errors
    errorData.detail.forEach(err => {
      const field = err.loc[err.loc.length - 1];
      const message = err.msg;
      showFieldError(field, message);
    });
  }
} catch (error) {
  console.error('Request failed:', error);
}
```

---

## 🛡️ Error Handling

### Error Response Formats

**401 Unauthorized (Missing/Invalid JWT):**
```json
{
  "detail": "Authentication required. Please provide a valid Bearer token."
}
```

**422 Validation Error:**
```json
{
  "error": "Validation Error",
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "years"],
      "msg": "Input should be greater than or equal to 1",
      "input": 0
    }
  ]
}
```

**429 Rate Limit Exceeded:**
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Maximum 100 requests per 60 seconds allowed.",
  "retry_after": 45
}
```

**404 Not Found:**
```json
{
  "detail": "Zone 'Z999' not found"
}
```

**500 Internal Server Error:**
```json
{
  "error": "HTTP 500",
  "detail": "Failed to retrieve citywide risk data: ..."
}
```

### Comprehensive Error Handler

```javascript
async function apiRequest(url, options = {}) {
  try {
    const response = await fetch(url, options);
    
    // Success
    if (response.ok) {
      return await response.json();
    }
    
    // Handle errors
    switch (response.status) {
      case 401:
        // Unauthorized - redirect to login
        console.error('Authentication required');
        redirectToLogin();
        throw new Error('Please log in to access this resource');
      
      case 422:
        // Validation error
        const validationError = await response.json();
        console.error('Validation errors:', validationError.detail);
        throw new Error('Invalid input data');
      
      case 429:
        // Rate limit exceeded
        const rateLimitError = await response.json();
        const retryAfter = response.headers.get('Retry-After');
        console.error(`Rate limited. Retry after ${retryAfter}s`);
        throw new Error(`Too many requests. Please wait ${retryAfter} seconds.`);
      
      case 404:
        // Not found
        const notFoundError = await response.json();
        console.error('Resource not found:', notFoundError.detail);
        throw new Error('Resource not found');
      
      case 500:
        // Server error
        console.error('Server error');
        throw new Error('Server error. Please try again later.');
      
      default:
        throw new Error(`Unexpected error: ${response.status}`);
    }
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}

// Usage
try {
  const data = await apiRequest('http://localhost:3001/api/v1/citywide-risk');
  // Process data
} catch (error) {
  // Show user-friendly error message
  showErrorNotification(error.message);
}
```

---

## 📋 Complete Example: React Component

```javascript
import React, { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.REACT_APP_SUPABASE_URL,
  process.env.REACT_APP_SUPABASE_ANON_KEY
);

const ForecastComponent = () => {
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [rateLimitInfo, setRateLimitInfo] = useState({});

  const generateForecast = async (years = 5) => {
    setLoading(true);
    setError(null);

    try {
      // Get JWT token from Supabase
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        setError('Please log in to generate forecasts');
        return;
      }

      const response = await fetch(
        'http://localhost:3001/api/v1/forecast/',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${session.access_token}`
          },
          body: JSON.stringify({
            years: years,
            include_climate_factors: true
          })
        }
      );

      // Update rate limit info
      setRateLimitInfo({
        limit: response.headers.get('X-RateLimit-Limit'),
        remaining: response.headers.get('X-RateLimit-Remaining'),
        reset: response.headers.get('X-RateLimit-Reset')
      });

      // Handle response
      if (response.ok) {
        const data = await response.json();
        setForecast(data);
      } else if (response.status === 401) {
        setError('Authentication failed. Please log in again.');
      } else if (response.status === 422) {
        const validationError = await response.json();
        setError(`Invalid input: ${validationError.detail[0].msg}`);
      } else if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After');
        setError(`Rate limit exceeded. Please wait ${retryAfter} seconds.`);
      } else {
        setError('Failed to generate forecast. Please try again.');
      }
    } catch (err) {
      console.error('Forecast error:', err);
      setError('Network error. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>Flood Risk Forecast</h2>
      
      {/* Rate Limit Info */}
      <div className="rate-limit-info">
        Requests remaining: {rateLimitInfo.remaining}/{rateLimitInfo.limit}
      </div>

      {/* Generate Button */}
      <button 
        onClick={() => generateForecast(5)}
        disabled={loading}
      >
        {loading ? 'Generating...' : 'Generate 5-Year Forecast'}
      </button>

      {/* Error Display */}
      {error && <div className="error">{error}</div>}

      {/* Forecast Display */}
      {forecast && (
        <div className="forecast">
          <h3>Forecast Results</h3>
          {forecast.data.map(prediction => (
            <div key={prediction.year} className={`risk-${prediction.risk_category.toLowerCase()}`}>
              <strong>{prediction.year}:</strong> {prediction.risk_category} 
              (Score: {prediction.risk_score})
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ForecastComponent;
```

---

## 🔗 API Base URLs

**Development:**
```javascript
const API_BASE_URL = 'http://localhost:3001';
```

**Production:**
```javascript
const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'https://your-backend-domain.com';
```

---

## 📝 Summary Checklist

- [ ] Always include `Authorization: Bearer <token>` for protected endpoints
- [ ] Handle rate limit headers and 429 errors gracefully
- [ ] Validate input client-side before sending (better UX)
- [ ] Implement comprehensive error handling for all status codes
- [ ] Cache responses when appropriate
- [ ] Debounce user inputs to reduce request volume
- [ ] Display rate limit info to users
- [ ] Test with invalid inputs to verify error handling
- [ ] Never send user_id in request body (always from JWT)

---

**Last Updated:** 2026-02-02  
**Backend Version:** 1.0  
**For Frontend Developers** 👨‍💻👩‍💻
