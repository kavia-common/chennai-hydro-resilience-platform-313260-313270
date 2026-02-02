# CHRIS Backend Performance Optimizations

## Overview

This document describes the performance optimizations implemented in the CHRIS Backend API to ensure efficient handling of read-heavy operations, proper resource management, and scalability.

## Implemented Optimizations

### 1. Supabase Client Reuse (Singleton Pattern)

**File:** `src/utils/supabase_client.py`

- Implemented singleton pattern for Supabase client to ensure connection reuse
- Prevents creating multiple client instances and connection pool exhaustion
- Thread-safe implementation with global client instance

**Benefits:**
- Reduced connection overhead
- Better connection pool management
- Improved memory efficiency

### 2. Response Caching with TTL

**File:** `src/utils/cache.py`

- In-memory cache with Time-To-Live (TTL) support
- Thread-safe operations using locks
- Automatic cleanup of expired entries every 5 minutes
- Cache key generation based on query parameters

**Cache Strategy:**
- **Citywide Risk Data:** 10-minute TTL (600s)
- **Sponge Zones Collection:** 10-minute TTL (600s)
- **Individual Zone Details:** 15-minute TTL (900s)
- **Empty Results:** 1-minute TTL (60s) to prevent repeated DB queries

**Cache Invalidation:**
```python
from src.utils.cache import invalidate_cache

# Invalidate all citywide risk caches
invalidate_cache("citywide_risk")

# Invalidate all sponge zone caches
invalidate_cache("sponge_zones")
```

**Note for Production:**
For distributed systems with multiple backend instances, replace the in-memory cache with Redis or Memcached for shared caching across instances.

### 3. Pagination for List Endpoints

**File:** `src/utils/pagination.py`

- Offset-based pagination for efficient handling of large datasets
- Configurable limits (1-1000 items per page, defaults: 50 for citywide, 100 for zones)
- Pagination metadata in responses (total count, current page, has_more, etc.)

**Endpoints with Pagination:**
- `GET /api/v1/citywide-risk` - Default limit: 50, max: 1000
- `GET /api/v1/map/sponge-zones` - Default limit: 100, max: 500

**Example Request:**
```bash
GET /api/v1/citywide-risk?limit=50&offset=0&start_year=2024
```

**Response Structure:**
```json
{
  "success": true,
  "data": [...],
  "summary": {
    "total_years": 150,
    "returned_years": 50,
    "pagination": {
      "total_count": 150,
      "limit": 50,
      "offset": 0,
      "current_page": 1,
      "total_pages": 3,
      "has_more": true,
      "next_offset": 50
    }
  }
}
```

### 4. Structured Logging with Correlation IDs

**File:** `src/utils/structured_logger.py`

- Request-scoped correlation IDs for distributed tracing
- Correlation IDs added to response headers (`X-Correlation-ID`)
- Support for JSON-formatted structured logs (optional configuration)
- Thread-safe using context variables for async operations

**Benefits:**
- Trace requests across multiple services
- Better debugging and troubleshooting
- Improved log aggregation and analysis

**Example Log Output:**
```
2024-02-02 10:30:00 - INFO - Request started: GET /api/v1/citywide-risk
  correlation_id: 123e4567-e89b-12d3-a456-426614174000
  client_ip: 192.168.1.1
```

### 5. Optimized Supabase Queries

**File:** `src/utils/supabase_client.py` - `build_optimized_query()`

**Optimizations:**
- **Selective Field Filtering:** Specify exact fields needed instead of `SELECT *`
- **Proper Filter Order:** Apply filters before ordering for better query planning
- **Limit Application:** Always use limits to reduce data transfer
- **Index-Aware Queries:** Queries designed to leverage database indexes

**Example:**
```python
# Optimized query
query = build_optimized_query(
    table_name="citywide_risk",
    select_fields=["year", "risk_score", "risk_category"],
    filters={"risk_category": "High"},
    order_by="year",
    limit=50
)

# Instead of:
# query = supabase.table("citywide_risk").select("*").order("year")
```

### 6. Database Index Recommendations

**For optimal performance, create the following database indexes:**

#### citywide_risk table:
```sql
-- Composite index for filtered queries with ordering
CREATE INDEX idx_citywide_risk_year_category 
ON citywide_risk (year, risk_category, risk_score);

-- Additional index for risk category queries
CREATE INDEX idx_citywide_risk_category_score 
ON citywide_risk (risk_category, risk_score DESC);
```

#### zone_risk table:
```sql
-- Index for zone lookups and filtering
CREATE INDEX idx_zone_risk_category_score 
ON zone_risk (capacity_category, capacity_score DESC);

-- Index for terrain type filtering
CREATE INDEX idx_zone_risk_terrain 
ON zone_risk (terrain_type, capacity_score DESC);

-- zone_id should already have a primary key index
```

**Note:** These indexes are recommendations for the Supabase PostgreSQL database. Apply them using the Supabase SQL Editor or via database migrations.

## Performance Metrics

### Expected Improvements:

1. **Cache Hit Ratio:** 70-80% for repeated queries within TTL window
2. **Database Load Reduction:** 60-70% reduction in database queries for read-heavy endpoints
3. **Response Time Improvement:**
   - Cached responses: < 10ms
   - Uncached with indexes: 50-200ms (depending on dataset size)
   - Paginated queries: Consistent performance regardless of total dataset size

4. **Memory Usage:**
   - In-memory cache: ~1-5 MB for typical workload (auto-cleanup)
   - Supabase client singleton: Single connection pool

## Monitoring Recommendations

### Key Metrics to Monitor:

1. **Cache Performance:**
   - Cache hit ratio
   - Cache memory usage
   - Cache eviction rate

2. **Database Performance:**
   - Query execution time
   - Number of queries per minute
   - Database connection pool usage

3. **API Response Times:**
   - P50, P95, P99 latencies per endpoint
   - Correlation between cache hits and response times

4. **Resource Usage:**
   - Memory consumption
   - CPU usage
   - Network bandwidth

### Logging Cache Stats:

```python
from src.utils.cache import get_cache

# Get cache statistics
cache = get_cache()
stats = cache.stats()
print(stats)
# Output: {"total_entries": 25, "active_entries": 20, "expired_entries": 5}
```

## Scaling Considerations

### Current Implementation Limitations:

1. **In-Memory Cache:** Not shared across multiple backend instances
   - **Solution:** Migrate to Redis/Memcached for distributed caching

2. **Rate Limiter:** In-memory storage not shared across instances
   - **Solution:** Use Redis for shared rate limiting state

3. **Pagination:** Offset-based pagination can be slow for very large offsets
   - **Solution:** Consider cursor-based pagination for datasets > 100K records

### Production Deployment Recommendations:

1. **Enable Distributed Caching:**
   - Deploy Redis instance
   - Update `src/utils/cache.py` to use Redis backend
   - Share cache across all backend instances

2. **Database Connection Pooling:**
   - Configure Supabase connection pool size appropriately
   - Monitor connection usage and adjust as needed

3. **Load Balancing:**
   - Use load balancer (e.g., Nginx, AWS ALB) for multiple backend instances
   - Ensure sticky sessions if using in-memory cache (or migrate to Redis)

4. **Content Delivery Network (CDN):**
   - Cache static API responses (e.g., sponge zones) at CDN edge
   - Use appropriate Cache-Control headers

5. **Query Result Streaming:**
   - For very large datasets, consider implementing streaming responses
   - Use Server-Sent Events (SSE) or WebSockets for real-time updates

## Security Considerations

All existing security measures remain intact:
- JWT authentication enforcement not affected by caching
- Rate limiting still applies to all requests (cache hits still count)
- Input validation occurs before cache lookup
- RLS policies in Supabase still enforced
- Security logging includes correlation IDs for better audit trails

## Cache-Busting Strategy

When data is modified (writes), caches must be invalidated:

```python
from src.utils.cache import invalidate_cache

# After updating citywide risk data:
invalidate_cache("citywide_risk")

# After updating zone data:
invalidate_cache("sponge_zones")
invalidate_cache("zone_detail")
```

**Note:** Current implementation is read-focused. Write operations (POST, PUT, DELETE) should call `invalidate_cache()` to ensure data consistency.

## Testing Performance Optimizations

### 1. Test Cache Performance:
```bash
# First request (cold cache)
curl -w "@curl-format.txt" "http://localhost:3001/api/v1/citywide-risk"

# Second request (warm cache) - should be significantly faster
curl -w "@curl-format.txt" "http://localhost:3001/api/v1/citywide-risk"
```

### 2. Test Pagination:
```bash
# Get first page
curl "http://localhost:3001/api/v1/citywide-risk?limit=10&offset=0"

# Get second page
curl "http://localhost:3001/api/v1/citywide-risk?limit=10&offset=10"
```

### 3. Test Correlation IDs:
```bash
curl -H "X-Correlation-ID: test-12345" -v "http://localhost:3001/api/v1/citywide-risk"
# Response should include X-Correlation-ID header
```

### 4. Load Testing:
```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test endpoint under load
ab -n 1000 -c 10 "http://localhost:3001/api/v1/citywide-risk"
```

## Future Enhancements

1. **Redis Integration:** Distributed caching for multi-instance deployments
2. **Query Result Caching in Supabase:** Leverage Supabase's built-in caching
3. **GraphQL Support:** More efficient field selection and nested queries
4. **Response Compression:** Enable gzip/brotli compression for large responses
5. **Database Read Replicas:** Distribute read queries across replicas
6. **Materialized Views:** Pre-compute aggregate statistics in database
7. **Edge Caching:** Deploy backend at edge locations for reduced latency

## Support and Maintenance

- Monitor cache effectiveness regularly and adjust TTL values as needed
- Review database query performance and index usage monthly
- Update pagination limits based on actual usage patterns and performance metrics
- Consider implementing cache warming strategies for frequently accessed data

---

**Last Updated:** 2024-02-02  
**Version:** 1.0.0
