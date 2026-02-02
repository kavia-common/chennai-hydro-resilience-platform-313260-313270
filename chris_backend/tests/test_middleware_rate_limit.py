"""
Tests for rate limiting middleware.

Tests token bucket algorithm, rate limit enforcement, and headers.
"""
import pytest
import time
from fastapi import status
from unittest.mock import MagicMock


class TestRateLimiter:
    """Tests for RateLimiter class."""
    
    def test_rate_limiter_allows_requests_within_limit(self):
        """Test that requests within limit are allowed."""
        from src.middleware.rate_limit import RateLimiter
        
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        # Make 5 requests
        for i in range(5):
            is_allowed, headers = limiter.check_rate_limit("192.168.1.1")
            assert is_allowed is True
            assert headers["X-RateLimit-Remaining"] == 5 - i - 1
    
    def test_rate_limiter_blocks_requests_over_limit(self):
        """Test that requests over limit are blocked."""
        from src.middleware.rate_limit import RateLimiter
        
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        # Make 3 allowed requests
        for _ in range(3):
            is_allowed, _ = limiter.check_rate_limit("192.168.1.1")
            assert is_allowed is True
        
        # 4th request should be blocked
        is_allowed, headers = limiter.check_rate_limit("192.168.1.1")
        assert is_allowed is False
        assert headers["X-RateLimit-Remaining"] == 0
    
    def test_rate_limiter_resets_after_window(self):
        """Test that rate limit resets after time window."""
        from src.middleware.rate_limit import RateLimiter
        
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        
        # Use up limit
        limiter.check_rate_limit("192.168.1.1")
        limiter.check_rate_limit("192.168.1.1")
        is_allowed, _ = limiter.check_rate_limit("192.168.1.1")
        assert is_allowed is False
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be allowed again
        is_allowed, headers = limiter.check_rate_limit("192.168.1.1")
        assert is_allowed is True
        assert headers["X-RateLimit-Remaining"] == 1
    
    def test_rate_limiter_tracks_ips_separately(self):
        """Test that different IPs have separate limits."""
        from src.middleware.rate_limit import RateLimiter
        
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        # IP 1 uses up limit
        limiter.check_rate_limit("192.168.1.1")
        limiter.check_rate_limit("192.168.1.1")
        is_allowed, _ = limiter.check_rate_limit("192.168.1.1")
        assert is_allowed is False
        
        # IP 2 should still be allowed
        is_allowed, headers = limiter.check_rate_limit("192.168.1.2")
        assert is_allowed is True
    
    def test_rate_limiter_cleanup(self):
        """Test that old entries are cleaned up."""
        from src.middleware.rate_limit import RateLimiter
        
        limiter = RateLimiter(max_requests=100, window_seconds=1)
        limiter._cleanup_interval = 0  # Force cleanup every time
        
        # Add some entries
        limiter.check_rate_limit("192.168.1.1")
        limiter.check_rate_limit("192.168.1.2")
        
        # Wait for entries to expire
        time.sleep(2.1)
        
        # Trigger cleanup
        limiter._cleanup_old_entries()
        
        # Old entries should be removed
        assert len(limiter.requests) == 0


class TestGetClientIP:
    """Tests for client IP extraction."""
    
    def test_get_client_ip_from_x_forwarded_for(self):
        """Test extracting IP from X-Forwarded-For header."""
        from src.middleware.rate_limit import get_client_ip
        
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "203.0.113.1, 198.51.100.1"
        mock_request.client.host = "192.168.1.1"
        
        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.1"
    
    def test_get_client_ip_from_x_real_ip(self):
        """Test extracting IP from X-Real-IP header."""
        from src.middleware.rate_limit import get_client_ip
        
        mock_request = MagicMock()
        mock_request.headers.get.side_effect = lambda key: {
            "X-Forwarded-For": None,
            "X-Real-IP": "203.0.113.1"
        }.get(key)
        mock_request.client.host = "192.168.1.1"
        
        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.1"
    
    def test_get_client_ip_from_direct_connection(self):
        """Test extracting IP from direct connection."""
        from src.middleware.rate_limit import get_client_ip
        
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client.host = "192.168.1.1"
        
        ip = get_client_ip(mock_request)
        assert ip == "192.168.1.1"


class TestRateLimitMiddleware:
    """Tests for rate limit middleware function."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_middleware_adds_headers(self, client):
        """Test that rate limit headers are added to response."""
        response = client.get("/")
        
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
    
    @pytest.mark.asyncio
    async def test_rate_limit_middleware_blocks_excess_requests(self, client):
        """Test that middleware blocks requests over limit."""
        from src.middleware.rate_limit import _rate_limiter
        
        # Store original max and set a lower limit for testing
        original_max = _rate_limiter.max_requests
        _rate_limiter.max_requests = 5
        
        try:
            # Make requests up to the limit
            responses = []
            for i in range(6):  # One more than limit
                response = client.get("/")
                responses.append(response)
            
            # Last response should be rate limited
            last_response = responses[-1]
            assert last_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert "Rate limit exceeded" in last_response.json()["detail"]["error"]
        finally:
            # Restore original limit
            _rate_limiter.max_requests = original_max
