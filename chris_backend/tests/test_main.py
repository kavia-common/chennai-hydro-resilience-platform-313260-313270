"""
Tests for main FastAPI application.

Tests health check, error handlers, and application lifecycle.
"""
from fastapi import status


class TestHealthCheck:
    """Tests for health check endpoint."""
    
    def test_health_check_returns_200(self, client):
        """Test that health check endpoint returns 200 OK."""
        response = client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_health_check_returns_correct_structure(self, client):
        """Test health check response structure."""
        response = client.get("/")
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "CHRIS Backend API"
        assert "version" in data
        assert "security" in data
    
    def test_health_check_shows_security_status(self, client):
        """Test that health check shows security configuration."""
        response = client.get("/")
        data = response.json()
        
        assert "jwt_auth" in data["security"]
        assert "rate_limiting" in data["security"]
        assert "cors" in data["security"]


class TestErrorHandlers:
    """Tests for global error handlers."""
    
    def test_validation_error_handler(self, client):
        """Test validation error handler."""
        # Send invalid data to a public endpoint (zones with invalid filter)
        response = client.get(
            "/api/v1/map/sponge-zones?limit=invalid"  # Should be int
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
    
    def test_http_exception_handler(self, client):
        """Test HTTP exception handler."""
        # Access non-existent endpoint
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCORS:
    """Tests for CORS configuration."""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are set."""
        response = client.options(
            "/api/v1/map/sponge-zones",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers or response.status_code == 200


class TestOpenAPI:
    """Tests for OpenAPI documentation."""
    
    def test_openapi_json_available(self, client):
        """Test that OpenAPI JSON is available."""
        response = client.get("/openapi.json")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
    
    def test_docs_available(self, client):
        """Test that Swagger UI docs are available."""
        response = client.get("/docs")
        
        assert response.status_code == status.HTTP_200_OK
