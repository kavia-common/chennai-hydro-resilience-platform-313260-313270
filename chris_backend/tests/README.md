# CHRIS Backend Test Suite

Comprehensive test coverage for Chennai Hydro-Resilience Intelligence System backend.

## Test Organization

### Test Modules

- **test_main.py** - Main application tests (health check, error handlers, CORS, OpenAPI)
- **test_routes_forecast.py** - Forecast API endpoint tests (authentication, validation, predictions)
- **test_routes_zones.py** - Sponge zones API endpoint tests (GeoJSON, filtering, pagination)
- **test_routes_citywide.py** - Citywide risk API endpoint tests (statistics, filtering)
- **test_middleware_auth.py** - JWT authentication middleware tests
- **test_middleware_rate_limit.py** - Rate limiting middleware tests
- **test_utils_cache.py** - Caching utility tests
- **test_schemas.py** - Pydantic schema validation tests
- **test_integration.py** - End-to-end integration tests

## Running Tests

### Run All Tests
```bash
source venv/bin/activate
pytest tests/ -v
```

### Run Specific Test Module
```bash
pytest tests/test_routes_forecast.py -v
```

### Run With Coverage
```bash
pytest tests/ --cov=src --cov-report=html --cov-report=term
```

### Run Tests Without Warnings
```bash
pytest tests/ -v --disable-warnings
```

## Test Coverage Goals

Target: **Near 100% coverage** of backend codebase

### Coverage by Module

- **API Routes** (forecast, zones, citywide): ~95%
- **Middleware** (auth, rate_limit): ~90%
- **Utilities** (cache, supabase_client, pagination, logging): ~85%
- **Schemas** (validation): ~100%
- **Main Application**: ~90%

## Test Fixtures

Key fixtures defined in `conftest.py`:

- `client` - TestClient for making API requests
- `auth_headers` - Valid JWT token headers for authenticated requests
- `mock_supabase_client` - Mocked Supabase client
- `sample_citywide_risk_data` - Sample flood risk data
- `sample_zone_data` - Sample sponge zone GeoJSON data
- `mock_cache` - Mocked in-memory cache

## Test Categories

### Unit Tests
Test individual functions and classes in isolation.

### Integration Tests
Test complete request-response workflows across multiple components.

### Security Tests
- JWT authentication and authorization
- Rate limiting enforcement
- Input validation and sanitization
- CORS configuration

### Performance Tests
- Caching effectiveness
- Pagination handling
- Query optimization

## Continuous Integration

Tests are designed to run in CI/CD pipelines with:
- Non-interactive mode
- No user input required
- Deterministic results
- Fast execution (< 10 seconds)

## Known Test Scenarios

### Authentication
- Valid JWT token acceptance
- Invalid token rejection
- Expired token handling
- Missing token error messages

### Rate Limiting
- Request counting per IP
- Window expiration
- Header inclusion (X-RateLimit-*)
- 429 status code on limit exceeded

### Data Validation
- Pydantic schema enforcement
- Range validation (years 1-10, scores 0-100)
- Category validation (Low/Moderate/High/Critical)
- Input sanitization (SQL injection, XSS)

### Caching
- Cache hits vs misses
- TTL expiration
- Pattern-based invalidation
- Statistics tracking

## Mocking Strategy

Tests use `unittest.mock` for:
- Supabase database calls
- JWT token verification
- Cache operations
- External API calls

This ensures:
- Fast test execution
- No external dependencies
- Predictable test data
- Isolated unit testing
