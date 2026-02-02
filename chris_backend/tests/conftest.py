"""
Pytest configuration and shared fixtures for CHRIS backend tests.

Provides test client, mock data, and utilities for all test modules.
"""
import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime
from typing import Dict, Any, List


# Set test environment variables before importing app
os.environ["SUPABASE_URL"] = "https://test-project.supabase.co"
os.environ["SUPABASE_KEY"] = "test-key-12345"
os.environ["SUPABASE_JWT_SECRET"] = "test-jwt-secret-12345"
os.environ["RATE_LIMIT_MAX"] = "100"
os.environ["RATE_LIMIT_WINDOW_S"] = "60"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000"
os.environ["NODE_ENV"] = "test"


@pytest.fixture(scope="session")
def test_env():
    """Test environment variables."""
    return {
        "SUPABASE_URL": os.environ["SUPABASE_URL"],
        "SUPABASE_KEY": os.environ["SUPABASE_KEY"],
        "SUPABASE_JWT_SECRET": os.environ["SUPABASE_JWT_SECRET"],
    }


@pytest.fixture(scope="function")
def mock_supabase_client():
    """Mock Supabase client for testing."""
    mock_client = MagicMock()
    
    # Mock table method to return a query builder
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    
    # Mock query builder methods (chainable)
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.offset.return_value = mock_table
    
    # Mock execute to return mock response
    mock_response = MagicMock()
    mock_response.data = []
    mock_response.count = 0  # Ensure count is int, not MagicMock
    mock_table.execute.return_value = mock_response
    
    return mock_client


@pytest.fixture(scope="function")
def app():
    """FastAPI app instance with mocked dependencies."""
    with patch("src.utils.supabase_client.get_supabase_client") as mock_get_client:
        # Configure mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Import app after patching
        from src.api.main import app
        yield app


@pytest.fixture(scope="function")
def client(app):
    """Test client for making requests."""
    return TestClient(app)


@pytest.fixture
def mock_jwt_token():
    """Valid mock JWT token for testing authentication."""
    from jose import jwt
    
    payload = {
        "sub": "test-user-123",
        "email": "test@example.com",
        "iss": "https://test-project.supabase.co/auth/v1",
        "iat": datetime.utcnow().timestamp(),
        "exp": datetime.utcnow().timestamp() + 3600
    }
    
    token = jwt.encode(
        payload,
        os.environ["SUPABASE_JWT_SECRET"],
        algorithm="HS256"
    )
    
    return token


@pytest.fixture
def auth_headers(mock_jwt_token):
    """Authorization headers with valid JWT token."""
    return {"Authorization": f"Bearer {mock_jwt_token}"}


@pytest.fixture
def sample_citywide_risk_data() -> List[Dict[str, Any]]:
    """Sample citywide risk data for testing."""
    return [
        {
            "id": "risk-1",
            "year": 2025,
            "risk_score": 65.5,
            "risk_category": "Moderate",
            "oni_anomaly": 0.5,
            "iod_anomaly": 0.3,
            "predicted_rainfall_mm": 1250.5,
            "confidence": 0.82,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z"
        },
        {
            "id": "risk-2",
            "year": 2026,
            "risk_score": 72.3,
            "risk_category": "High",
            "oni_anomaly": 1.2,
            "iod_anomaly": 0.6,
            "predicted_rainfall_mm": 1450.0,
            "confidence": 0.85,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z"
        },
        {
            "id": "risk-3",
            "year": 2027,
            "risk_score": 88.7,
            "risk_category": "Critical",
            "oni_anomaly": 1.8,
            "iod_anomaly": 0.9,
            "predicted_rainfall_mm": 1650.8,
            "confidence": 0.87,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z"
        }
    ]


@pytest.fixture
def sample_zone_data() -> List[Dict[str, Any]]:
    """Sample sponge zone data for testing."""
    return [
        {
            "zone_id": "Z001",
            "zone_name": "Adyar River Basin Zone 4",
            "capacity_score": 85.2,
            "capacity_category": "High",
            "vv_amplitude": -12.5,
            "vh_backscatter": -18.3,
            "mndwi": 0.65,
            "ndvi": 0.25,
            "terrain_type": "River Basin",
            "recommendation": "Priority desilting recommended",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [80.2707, 13.0067],
                        [80.2720, 13.0067],
                        [80.2720, 13.0080],
                        [80.2707, 13.0080],
                        [80.2707, 13.0067]
                    ]
                ]
            }
        },
        {
            "zone_id": "Z002",
            "zone_name": "Cooum River Wetland",
            "capacity_score": 62.8,
            "capacity_category": "Moderate",
            "vv_amplitude": -15.2,
            "vh_backscatter": -20.1,
            "mndwi": 0.45,
            "ndvi": 0.35,
            "terrain_type": "Wetland",
            "recommendation": "Monitor water levels",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [80.2800, 13.0100],
                        [80.2850, 13.0100],
                        [80.2850, 13.0150],
                        [80.2800, 13.0150],
                        [80.2800, 13.0100]
                    ]
                ]
            }
        }
    ]


@pytest.fixture
def mock_cache():
    """Mock cache for testing."""
    cache_data = {}
    
    mock = MagicMock()
    
    # Configure get method
    def mock_get(key):
        return cache_data.get(key)
    
    # Configure set method
    def mock_set(key, value, ttl_seconds=300):
        cache_data[key] = value
    
    # Configure invalidate method
    def mock_invalidate(key):
        cache_data.pop(key, None)
    
    # Configure invalidate_pattern method
    def mock_invalidate_pattern(pattern):
        keys_to_delete = [k for k in cache_data.keys() if pattern in k]
        for k in keys_to_delete:
            cache_data.pop(k)
    
    # Configure clear method
    def mock_clear():
        cache_data.clear()
    
    # Configure stats method
    def mock_stats():
        return {
            "total_entries": len(cache_data),
            "active_entries": len(cache_data),
            "expired_entries": 0
        }
    
    mock.get.side_effect = mock_get
    mock.set.side_effect = mock_set
    mock.invalidate.side_effect = mock_invalidate
    mock.invalidate_pattern.side_effect = mock_invalidate_pattern
    mock.clear.side_effect = mock_clear
    mock.stats.side_effect = mock_stats
    
    return mock


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter between tests."""
    from src.middleware.rate_limit import _rate_limiter
    _rate_limiter.requests.clear()
    yield
    _rate_limiter.requests.clear()


@pytest.fixture
def mock_ml_model():
    """Mock ML model for testing predictions."""
    mock_model = MagicMock()
    mock_model.predict.return_value = [[0.655, 0.723, 0.887]]
    return mock_model
