# CHRIS Backend API - Security Documentation

## Overview

The CHRIS Backend API implements multiple layers of security to protect against common vulnerabilities and ensure data integrity.

## Security Features

### 1. JWT Authentication (Supabase)

**Protected Endpoints:**
- `POST /api/v1/forecast/` - Requires valid JWT token

**Implementation:**
- JWT tokens are verified using Supabase JWT secret
- Tokens must be passed in `Authorization: Bearer <token>` header
- User context (user_id) is extracted from token's `sub` claim
- Tokens are validated for signature, expiration, and issuer

**Configuration:**
```env
SUPABASE_JWT_SECRET=your_jwt_secret_from_supabase_dashboard
```

**How to Get JWT Secret:**
1. Go to Supabase Dashboard → Settings → API
2. Copy the "JWT Secret" value
3. Add it to your `.env` file

**Example Request:**
```bash
curl -X POST https://your-backend.com/api/v1/forecast/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{"years": 5, "include_climate_factors": true}'
```

### 2. Rate Limiting

**Configuration:**
- Default: 100 requests per 60 seconds per IP address
- Configurable via environment variables

**Environment Variables:**
```env
RATE_LIMIT_WINDOW_S=60
RATE_LIMIT_MAX=100
```

**Response Headers:**
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when the limit resets

**Error Response (429):**
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Maximum 100 requests per 60 seconds allowed.",
  "retry_after": 45
}
```

### 3. CORS Protection

**Tightened CORS Configuration:**
- Only allows configured frontend origins
- Restricts methods and headers
- Credentials support for authenticated requests

**Environment Variables:**
```env
ALLOWED_ORIGINS=https://your-frontend.com,http://localhost:3000
ALLOWED_HEADERS=Content-Type,Authorization,X-Requested-With
ALLOWED_METHODS=GET,POST,PUT,DELETE,PATCH,OPTIONS
CORS_MAX_AGE=3600
```

**Default Behavior:**
- If `ALLOWED_ORIGINS` is not set, falls back to `FRONTEND_URL`
- Wildcard (`*`) is only used if explicitly configured

### 4. Input Validation & Sanitization

**Pydantic Schema Validation:**
- All inputs are validated against strict Pydantic schemas
- Type checking enforced (int, float, str, bool)
- Range validation (e.g., years: 1-10, risk_score: 0-100)
- String length limits to prevent buffer overflow attacks
- Field-level validators for additional checks

**Example Validations:**
```python
# Forecast Request
years: int = Field(ge=1, le=10)  # Must be 1-10
risk_score: float = Field(ge=0.0, le=100.0)  # Must be 0-100
zone_id: str = Field(min_length=1, max_length=20)  # Length constrained

# Custom validators prevent injection
@field_validator('zone_id')
def validate_zone_id(cls, v):
    if not v.replace('_', '').replace('-', '').isalnum():
        raise ValueError('Invalid zone_id format')
    return v
```

**Validation Error Response (422):**
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

### 5. Row-Level Security (RLS) Alignment

**Database Queries:**
- All Supabase queries respect RLS policies defined in the database
- User context from JWT is automatically applied by Supabase client
- No user_id is accepted from client input (always from JWT token)

**RLS Policies:**
```sql
-- Example: Users can only read their own forecasts
CREATE POLICY "Users can read own forecasts"
ON citywide_risk FOR SELECT
USING (auth.uid() = user_id);
```

### 6. Structured Security Logging

**Logged Events:**
- Authentication failures
- Rate limit violations
- Suspicious activity (invalid inputs, unusual patterns)
- Successful authentications (for audit trail)

**Log Format:**
```json
{
  "event_type": "auth_failure",
  "timestamp": "2026-02-02T12:00:00Z",
  "reason": "Invalid token",
  "client_ip": "192.168.1.100",
  "endpoint": "/api/v1/forecast/",
  "user_id": null
}
```

**Security Logger:**
- Separate logger (`security`) for security events
- All events include timestamp, IP, endpoint, and context
- Can be integrated with SIEM systems

## Security Best Practices

### For Developers

1. **Never expose JWT secrets:**
   - Keep `SUPABASE_JWT_SECRET` in `.env` file
   - Never commit `.env` to version control
   - Use different secrets for dev/staging/prod

2. **Always validate user context:**
   ```python
   # ✅ Correct: Get user_id from JWT token
   user_id = user["sub"]
   
   # ❌ Wrong: Accept user_id from client
   # user_id = request.body["user_id"]  # NEVER DO THIS
   ```

3. **Use dependencies for authentication:**
   ```python
   @router.post("/protected-endpoint")
   async def protected_route(user: Dict = Depends(get_current_user)):
       user_id = user["sub"]
       # ... protected logic
   ```

4. **Validate all inputs:**
   - Use Pydantic models for all request bodies
   - Add custom validators for complex rules
   - Set appropriate field constraints

5. **Handle errors securely:**
   - Don't expose stack traces to clients
   - Log detailed errors server-side
   - Return generic error messages to clients

### For Deployment

1. **Environment Configuration:**
   ```bash
   # Production .env
   NODE_ENV=production
   ALLOWED_ORIGINS=https://your-production-frontend.com
   RATE_LIMIT_MAX=50  # Lower limit for production
   TRUST_PROXY=true
   ```

2. **HTTPS Only:**
   - Always use HTTPS in production
   - Configure SSL/TLS certificates
   - Set secure cookie flags

3. **Monitoring:**
   - Set up alerts for rate limit violations
   - Monitor authentication failure patterns
   - Track suspicious activity logs

4. **Database Security:**
   - Enable RLS on all Supabase tables
   - Use service role key only for admin operations
   - Rotate secrets regularly

## Attack Mitigation

### SQL Injection
- **Protection:** Using Supabase client (parameterized queries)
- **Status:** ✅ Protected

### XSS (Cross-Site Scripting)
- **Protection:** Input validation, output encoding
- **Status:** ✅ Protected

### CSRF (Cross-Site Request Forgery)
- **Protection:** JWT tokens (not cookies), CORS restrictions
- **Status:** ✅ Protected

### Rate Limit Bypass
- **Protection:** IP-based rate limiting, token bucket algorithm
- **Status:** ✅ Protected (⚠️ Use Redis for distributed systems)

### JWT Token Theft
- **Protection:** HTTPS only, short token expiration, secure storage
- **Status:** ⚠️ Client-side responsibility

### DDoS (Distributed Denial of Service)
- **Protection:** Rate limiting, request timeout
- **Status:** ⚠️ Use WAF/CDN for production

## Security Checklist

Before deploying to production:

- [ ] `SUPABASE_JWT_SECRET` is configured
- [ ] `ALLOWED_ORIGINS` is set to specific domains (no `*`)
- [ ] Rate limiting is enabled and configured appropriately
- [ ] HTTPS is configured
- [ ] RLS policies are enabled on all database tables
- [ ] Security logging is configured
- [ ] Error messages don't expose sensitive information
- [ ] All environment variables are set correctly
- [ ] `.env` file is not in version control
- [ ] Monitoring and alerting are set up

## Reporting Security Issues

If you discover a security vulnerability, please email: security@chris-platform.example.com

Do not open public issues for security vulnerabilities.

---

**Last Updated:** 2026-02-02  
**Security Version:** 1.0  
**Status:** Hardened ✅
