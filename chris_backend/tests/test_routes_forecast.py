"""
Tests for forecast API routes.

Tests the temporal LSTM-based flood prediction endpoints with authentication.
"""
from fastapi import status
from unittest.mock import patch, MagicMock


class TestForecastEndpoint:
    """Tests for POST /api/v1/forecast/ endpoint."""
    
    def test_forecast_without_auth_returns_401(self, client):
        """Test that forecast endpoint requires authentication."""
        response = client.post(
            "/api/v1/forecast/",
            json={"years": 5, "include_climate_factors": True}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "authentication" in response.json()["detail"].lower()
    
    def test_forecast_with_invalid_token_returns_401(self, client):
        """Test that invalid JWT token is rejected."""
        headers = {"Authorization": "Bearer invalid-token-12345"}
        response = client.post(
            "/api/v1/forecast/",
            headers=headers,
            json={"years": 5, "include_climate_factors": True}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @patch("src.api.routes.forecast.get_supabase_client")
    def test_forecast_with_valid_auth_returns_predictions(
        self, mock_get_client, client, auth_headers, sample_citywide_risk_data
    ):
        """Test successful forecast generation with authentication."""
        # Mock Supabase response
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
        
        response = client.post(
            "/api/v1/forecast/",
            headers=auth_headers,
            json={"years": 5, "include_climate_factors": True}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 3
        assert "model_version" in data
        assert "generated_at" in data
    
    def test_forecast_validates_years_parameter(self, client, auth_headers):
        """Test that years parameter is validated (1-10 range)."""
        # Test years < 1
        response = client.post(
            "/api/v1/forecast/",
            headers=auth_headers,
            json={"years": 0, "include_climate_factors": True}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test years > 10
        response = client.post(
            "/api/v1/forecast/",
            headers=auth_headers,
            json={"years": 11, "include_climate_factors": True}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch("src.api.routes.forecast.get_supabase_client")
    def test_forecast_filters_climate_factors_when_not_requested(
        self, mock_get_client, client, auth_headers, sample_citywide_risk_data
    ):
        """Test that climate factors are filtered when include_climate_factors=False."""
        # Mock Supabase response
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
        
        response = client.post(
            "/api/v1/forecast/",
            headers=auth_headers,
            json={"years": 3, "include_climate_factors": False}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Climate factors should be None
        for record in data["data"]:
            assert record.get("oni_anomaly") is None
            assert record.get("iod_anomaly") is None
    
    @patch("src.api.routes.forecast.get_supabase_client")
    def test_forecast_handles_no_data(
        self, mock_get_client, client, auth_headers
    ):
        """Test forecast endpoint when no predictions are available."""
        # Mock empty Supabase response
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        
        mock_table.execute.return_value = mock_response
        mock_table.select.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.lte.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client
        
        # Mock predict_flood_risk to also return empty
        with patch("src.api.routes.forecast.predict_flood_risk", return_value=[]):
            response = client.post(
                "/api/v1/forecast/",
                headers=auth_headers,
                json={"years": 5}
            )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No predictions available" in response.json()["detail"]
    
    @patch("src.api.routes.forecast.get_supabase_client")
    def test_forecast_handles_database_error(
        self, mock_get_client, client, auth_headers
    ):
        """Test forecast endpoint handles database errors gracefully."""
        mock_client = MagicMock()
        mock_client.table.side_effect = Exception("Database connection failed")
        mock_get_client.return_value = mock_client
        
        response = client.post(
            "/api/v1/forecast/",
            headers=auth_headers,
            json={"years": 5}
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to generate forecast" in response.json()["detail"]
    
    def test_forecast_with_default_parameters(self, client, auth_headers):
        """Test forecast endpoint with default parameters."""
        with patch("src.api.routes.forecast.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_response = MagicMock()
            mock_response.data = []
            
            mock_table.execute.return_value = mock_response
            mock_table.select.return_value = mock_table
            mock_table.gte.return_value = mock_table
            mock_table.lte.return_value = mock_table
            mock_table.order.return_value = mock_table
            mock_client.table.return_value = mock_table
            mock_get_client.return_value = mock_client
            
            with patch("src.api.routes.forecast.predict_flood_risk", return_value=[]):
                # Should use default: years=5, include_climate_factors=True
                response = client.post("/api/v1/forecast/", headers=auth_headers, json={})
        
        # Should get 404 since no data, but validates defaults were accepted
        assert response.status_code == status.HTTP_404_NOT_FOUND
