"""
Rate limiting middleware for CHRIS Backend API.

Implements simple in-memory rate limiting with token bucket algorithm.
For production, consider Redis-based rate limiting for distributed systems.
"""
from fastapi import HTTPException, Request, status
from typing import Dict, Tuple
import time
import logging
from collections import defaultdict
from functools import wraps
import os

logger = logging.getLogger(__name__)

# Configuration
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW_S", "60"))  # seconds
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "100"))  # requests per window


class RateLimiter:
    """
    In-memory token bucket rate limiter.
    
    Tracks request counts per IP address within a sliding window.
    Not suitable for distributed systems (use Redis for multi-instance deployments).
    """
    
    def __init__(self, max_requests: int = RATE_LIMIT_MAX, window_seconds: int = RATE_LIMIT_WINDOW):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Storage: {ip_address: (request_count, window_start_time)}
        self.requests: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, time.time()))
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Clean up old entries every 5 minutes
    
    def _cleanup_old_entries(self):
        """
        Remove expired entries to prevent memory leak.
        Called periodically during check_rate_limit.
        """
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        expired_ips = [
            ip for ip, (_, start_time) in self.requests.items()
            if now - start_time > self.window_seconds * 2
        ]
        
        for ip in expired_ips:
            del self.requests[ip]
        
        self._last_cleanup = now
        if expired_ips:
            logger.debug(f"Cleaned up {len(expired_ips)} expired rate limit entries")
    
    def check_rate_limit(self, client_ip: str) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request should be allowed based on rate limit.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            Tuple of (is_allowed, headers_dict)
            headers_dict contains X-RateLimit-* headers
        """
        now = time.time()
        
        # Periodic cleanup
        self._cleanup_old_entries()
        
        # Get current state for this IP
        count, window_start = self.requests[client_ip]
        
        # Check if window has expired
        if now - window_start >= self.window_seconds:
            # Reset window
            count = 0
            window_start = now
        
        # Increment count
        count += 1
        self.requests[client_ip] = (count, window_start)
        
        # Calculate remaining requests and reset time
        remaining = max(0, self.max_requests - count)
        reset_time = int(window_start + self.window_seconds)
        
        headers = {
            "X-RateLimit-Limit": self.max_requests,
            "X-RateLimit-Remaining": remaining,
            "X-RateLimit-Reset": reset_time
        }
        
        # Check if limit exceeded
        if count > self.max_requests:
            logger.warning(
                f"Rate limit exceeded for IP {client_ip}: "
                f"{count} requests in {int(now - window_start)}s window"
            )
            return False, headers
        
        return True, headers


# Global rate limiter instance
_rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    
    Handles X-Forwarded-For and X-Real-IP headers for proxied requests.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address
    """
    # Check for proxy headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs (client, proxy1, proxy2, ...)
        # Take the first one (original client)
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection IP
    return request.client.host if request.client else "unknown"


async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware function to apply rate limiting to all requests.
    
    Add this to FastAPI app:
    ```python
    app.middleware("http")(rate_limit_middleware)
    ```
    
    Args:
        request: FastAPI request
        call_next: Next middleware/route handler
        
    Returns:
        Response with rate limit headers
        
    Raises:
        HTTPException: If rate limit exceeded (429 Too Many Requests)
    """
    client_ip = get_client_ip(request)
    
    # Check rate limit
    is_allowed, rate_headers = _rate_limiter.check_rate_limit(client_ip)
    
    if not is_allowed:
        logger.warning(f"Rate limit exceeded for IP: {client_ip} on {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Maximum {_rate_limiter.max_requests} "
                          f"requests per {_rate_limiter.window_seconds} seconds allowed.",
                "retry_after": rate_headers["X-RateLimit-Reset"] - int(time.time())
            },
            headers={
                **rate_headers,
                "Retry-After": str(rate_headers["X-RateLimit-Reset"] - int(time.time()))
            }
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers to response
    for header, value in rate_headers.items():
        response.headers[header] = str(value)
    
    return response


# PUBLIC_INTERFACE
def rate_limit(endpoint_name: str = "default"):
    """
    Decorator to apply rate limiting to specific endpoints.
    
    Usage:
    ```python
    @router.post("/sensitive-endpoint")
    @rate_limit(endpoint_name="forecast")
    async def forecast_endpoint():
        # ... endpoint logic
    ```
    
    Args:
        endpoint_name: Name for logging purposes
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = get_client_ip(request)
            is_allowed, rate_headers = _rate_limiter.check_rate_limit(client_ip)
            
            if not is_allowed:
                logger.warning(
                    f"Rate limit exceeded for IP: {client_ip} "
                    f"on endpoint: {endpoint_name}"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded for {endpoint_name}",
                    headers={
                        **rate_headers,
                        "Retry-After": str(rate_headers["X-RateLimit-Reset"] - int(time.time()))
                    }
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
