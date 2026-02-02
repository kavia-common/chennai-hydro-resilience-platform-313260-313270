"""
Integration tests for CHRIS backend.

End-to-end tests covering full request-response cycles.
"""
from fastapi import status
from unittest.mock import patch, MagicMock


class TestForecastIntegration:
    """Integration tests for forecast workflow."""
    
    @patch("src.api.routes.forecast.get_supabase_client")
    def test_full_forecast_workflow(
        self, mock_get_client, client, auth_headers, sample_citywide_risk_data
    ):
        """Test complete forecast generation workflow."""
        # Mock database
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_response = MagicMock()
        mock_response.data = sample_citywide_risk_data
        
        mock_table.execute.return_value = mock_response
        mock_table.select.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.lte.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client
        
        # Make request
        response = client.post(
            "/api/v1/forecast/",
            headers=auth_headers,
            json={"years": 5, "include_climate_factors": True}
        )
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["success"] is True
        assert len(data["data"]) > 0
        assert all("year" in record for record in data["data"])
        assert all("risk_score" in record for record in data["data"])
        assert "model_version" in data
        assert "generated_at" in data
        
        # Verify rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


class TestZonesIntegration:
    """Integration tests for zones workflow."""
    
    @patch("src.api.routes.zones.get_cache")
    @patch("src.api.routes.zones.get_supabase_client")
    def test_full_zones_workflow(
        self, mock_get_client, mock_get_cache, client, sample_zone_data, mock_cache
    ):
        """Test complete sponge zones retrieval workflow."""
        mock_get_cache.return_value = mock_cache
        
        # Mock database
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock main query with all chainable methods
        mock_main_query = MagicMock()
        mock_main_response = MagicMock()
        mock_main_response.data = sample_zone_data
        mock_main_query.select.return_value = mock_main_query
        mock_main_query.order.return_value = mock_main_query
        mock_main_query.limit.return_value = mock_main_query
        mock_main_query.offset.return_value = mock_main_query
        mock_main_query.eq.return_value = mock_main_query
        mock_main_query.execute.return_value = mock_main_response
        
        # Mock count query
        mock_count_query = MagicMock()
        mock_count_response = MagicMock()
        mock_count_response.count = 2  # Explicitly int
        mock_count_query.select.return_value = mock_count_query
        mock_count_query.eq.return_value = mock_count_query
        mock_count_query.execute.return_value = mock_count_response
        
        call_count = [0]
        def table_side_effect(table_name):
            call_count[0] += 1
            return mock_main_query if call_count[0] == 1 else mock_count_query
        
        mock_client.table.side_effect = table_side_effect
        
        # Make request
        response = client.get("/api/v1/map/sponge-zones")
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 2
        assert all(f["type"] == "Feature" for f in data["features"])
        assert all("geometry" in f for f in data["features"])
        assert all("properties" in f for f in data["features"])


class TestSecurityIntegration:
    """Integration tests for security features."""
    
    def test_rate_limiting_enforcement(self, client):
        """Test that rate limiting is enforced across requests."""
        from src.middleware.rate_limit import _rate_limiter
        
        # Temporarily set a lower limit for this test
        original_max = _rate_limiter.max_requests
        _rate_limiter.max_requests = 5
        
        try:
            # Make requests up to limit
            successful_requests = 0
            for i in range(7):  # Try more than limit
                response = client.get("/")
                if response.status_code == status.HTTP_200_OK:
                    successful_requests += 1
                elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                    break
            
            # Should have hit rate limit at 5
            assert successful_requests <= 5
            assert successful_requests > 0
        finally:
            # Restore original limit
            _rate_limiter.max_requests = original_max
    
    def test_authentication_flow(self, client, mock_jwt_token):
        """Test authentication across multiple requests."""
        headers = {"Authorization": f"Bearer {mock_jwt_token}"}
        
        with patch("src.api.routes.forecast.get_supabase_client") as mock_client:
            mock_client_inst = MagicMock()
            mock_table = MagicMock()
            mock_response = MagicMock()
            mock_response.data = []
            
            mock_table.execute.return_value = mock_response
            mock_table.select.return_value = mock_table
            mock_table.gte.return_value = mock_table
            mock_table.lte.return_value = mock_table
            mock_table.order.return_value = mock_table
            mock_client_inst.table.return_value = mock_table
            mock_client.return_value = mock_client_inst
            
            with patch("src.api.routes.forecast.predict_flood_risk", return_value=[]):
                # Without auth - should fail
                response1 = client.post("/api/v1/forecast/", json={"years": 5})
                assert response1.status_code == status.HTTP_401_UNAUTHORIZED
                
                # With auth - should succeed (or get 404 for no data)
                response2 = client.post("/api/v1/forecast/", headers=headers, json={"years": 5})
                assert response2.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


class TestCachingIntegration:
    """Integration tests for caching behavior."""
    
    @patch("src.api.routes.zones.get_cache")
    @patch("src.api.routes.zones.get_supabase_client")
    def test_caching_reduces_database_calls(
        self, mock_get_client, mock_get_cache, client, mock_cache, sample_zone_data
    ):
        """Test that caching reduces database queries."""
        mock_get_cache.return_value = mock_cache
        
        execute_count = [0]
        
        def mock_execute_main():
            execute_count[0] += 1
            mock_resp = MagicMock()
            mock_resp.data = sample_zone_data
            return mock_resp
        
        def mock_execute_count():
            execute_count[0] += 1
            mock_resp = MagicMock()
            mock_resp.count = 2  # Explicitly int
            return mock_resp
        
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock main query with all chainable methods
        mock_main_query = MagicMock()
        mock_main_query.select.return_value = mock_main_query
        mock_main_query.order.return_value = mock_main_query
        mock_main_query.limit.return_value = mock_main_query
        mock_main_query.offset.return_value = mock_main_query
        mock_main_query.eq.return_value = mock_main_query
        mock_main_query.execute.side_effect = mock_execute_main
        
        # Mock count query
        mock_count_query = MagicMock()
        mock_count_query.select.return_value = mock_count_query
        mock_count_query.eq.return_value = mock_count_query
        mock_count_query.execute.side_effect = mock_execute_count
        
        table_call_count = [0]
        def table_side_effect(table_name):
            table_call_count[0] += 1
            return mock_main_query if table_call_count[0] % 2 == 1 else mock_count_query
        
        mock_client.table.side_effect = table_side_effect
        
        # First request - hits database
        response1 = client.get("/api/v1/map/sponge-zones")
        assert response1.status_code == status.HTTP_200_OK
        assert execute_count[0] == 2  # Main query + count query
        
        # Second request - uses cache
        response2 = client.get("/api/v1/map/sponge-zones")
        assert response2.status_code == status.HTTP_200_OK
        assert execute_count[0] == 2  # Should not increase
