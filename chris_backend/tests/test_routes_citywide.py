"""
Tests for citywide risk API routes.

Tests the aggregate flood risk data endpoints.
"""
from fastapi import status
from unittest.mock import patch, MagicMock


class TestCitywideRiskEndpoint:
    """Tests for GET /api/v1/citywide-risk endpoint."""
    
    @patch("src.api.routes.citywide.get_cache")
    @patch("src.api.routes.citywide.get_supabase_client")
    def test_get_citywide_risk_returns_data(
        self, mock_get_client, mock_get_cache, client, sample_citywide_risk_data, mock_cache
    ):
        """Test that citywide risk endpoint returns data with statistics."""
        mock_get_cache.return_value = mock_cache
        
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Create separate mocks for main query and count query
        mock_main_query = MagicMock()
        mock_count_query = MagicMock()
        
        # Setup main query response
        mock_main_response = MagicMock()
        mock_main_response.data = sample_citywide_risk_data
        mock_main_query.select.return_value = mock_main_query
        mock_main_query.order.return_value = mock_main_query
        mock_main_query.limit.return_value = mock_main_query
        mock_main_query.offset.return_value = mock_main_query
        mock_main_query.gte.return_value = mock_main_query
        mock_main_query.lte.return_value = mock_main_query
        mock_main_query.eq.return_value = mock_main_query
        mock_main_query.execute.return_value = mock_main_response
        
        # Setup count query response
        mock_count_response = MagicMock()
        mock_count_response.count = 3  # Explicitly set as int
        mock_count_query.select.return_value = mock_count_query
        mock_count_query.gte.return_value = mock_count_query
        mock_count_query.lte.return_value = mock_count_query
        mock_count_query.eq.return_value = mock_count_query
        mock_count_query.execute.return_value = mock_count_response
        
        # Return different mocks for different table() calls
        call_count = [0]
        def table_side_effect(table_name):
            call_count[0] += 1
            return mock_main_query if call_count[0] == 1 else mock_count_query
        
        mock_client.table.side_effect = table_side_effect
        
        response = client.get("/api/v1/citywide-risk")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 3
        assert "summary" in data
        assert data["summary"]["highest_risk_year"] == 2027
        assert data["summary"]["highest_risk_score"] == 88.7
    
    @patch("src.api.routes.citywide.get_cache")
    @patch("src.api.routes.citywide.get_supabase_client")
    def test_get_citywide_risk_filters_by_year_range(
        self, mock_get_client, mock_get_cache, client, sample_citywide_risk_data, mock_cache
    ):
        """Test filtering citywide risk by year range."""
        mock_get_cache.return_value = mock_cache
        
        filtered_data = [r for r in sample_citywide_risk_data if r["year"] >= 2026]
        
        mock_client = MagicMock()
        
        # Create separate mocks for main and count queries
        mock_main_query = MagicMock()
        mock_count_query = MagicMock()
        
        mock_main_response = MagicMock()
        mock_main_response.data = filtered_data
        mock_main_query.select.return_value = mock_main_query
        mock_main_query.order.return_value = mock_main_query
        mock_main_query.limit.return_value = mock_main_query
        mock_main_query.offset.return_value = mock_main_query
        mock_main_query.gte.return_value = mock_main_query
        mock_main_query.lte.return_value = mock_main_query
        mock_main_query.eq.return_value = mock_main_query
        mock_main_query.execute.return_value = mock_main_response
        
        mock_count_response = MagicMock()
        mock_count_response.count = 2  # Explicitly int
        mock_count_query.select.return_value = mock_count_query
        mock_count_query.gte.return_value = mock_count_query
        mock_count_query.lte.return_value = mock_count_query
        mock_count_query.eq.return_value = mock_count_query
        mock_count_query.execute.return_value = mock_count_response
        
        call_count = [0]
        def table_side_effect(table_name):
            call_count[0] += 1
            return mock_main_query if call_count[0] == 1 else mock_count_query
        
        mock_client.table.side_effect = table_side_effect
        mock_get_client.return_value = mock_client
        
        response = client.get("/api/v1/citywide-risk?start_year=2026&end_year=2027")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 2
        assert all(r["year"] >= 2026 for r in data["data"])
    
    def test_get_citywide_risk_validates_year_range(self, client):
        """Test that year range is validated."""
        # Test start_year > end_year
        response = client.get("/api/v1/citywide-risk?start_year=2027&end_year=2025")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test year out of bounds
        response = client.get("/api/v1/citywide-risk?start_year=1999")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch("src.api.routes.citywide.get_cache")
    @patch("src.api.routes.citywide.get_supabase_client")
    def test_get_citywide_risk_filters_by_category(
        self, mock_get_client, mock_get_cache, client, sample_citywide_risk_data, mock_cache
    ):
        """Test filtering citywide risk by risk category."""
        mock_get_cache.return_value = mock_cache
        
        filtered_data = [r for r in sample_citywide_risk_data if r["risk_category"] == "Critical"]
        
        mock_client = MagicMock()
        
        # Create separate mocks
        mock_main_query = MagicMock()
        mock_count_query = MagicMock()
        
        mock_main_response = MagicMock()
        mock_main_response.data = filtered_data
        mock_main_query.select.return_value = mock_main_query
        mock_main_query.order.return_value = mock_main_query
        mock_main_query.limit.return_value = mock_main_query
        mock_main_query.offset.return_value = mock_main_query
        mock_main_query.gte.return_value = mock_main_query
        mock_main_query.lte.return_value = mock_main_query
        mock_main_query.eq.return_value = mock_main_query
        mock_main_query.execute.return_value = mock_main_response
        
        mock_count_response = MagicMock()
        mock_count_response.count = 1  # Explicitly int
        mock_count_query.select.return_value = mock_count_query
        mock_count_query.gte.return_value = mock_count_query
        mock_count_query.lte.return_value = mock_count_query
        mock_count_query.eq.return_value = mock_count_query
        mock_count_query.execute.return_value = mock_count_response
        
        call_count = [0]
        def table_side_effect(table_name):
            call_count[0] += 1
            return mock_main_query if call_count[0] == 1 else mock_count_query
        
        mock_client.table.side_effect = table_side_effect
        mock_get_client.return_value = mock_client
        
        response = client.get("/api/v1/citywide-risk?risk_category=Critical")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["risk_category"] == "Critical"
    
    def test_get_citywide_risk_validates_risk_category(self, client):
        """Test that risk category is validated."""
        response = client.get("/api/v1/citywide-risk?risk_category=Invalid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch("src.api.routes.citywide.get_cache")
    @patch("src.api.routes.citywide.get_supabase_client")
    def test_get_citywide_risk_pagination(
        self, mock_get_client, mock_get_cache, client, sample_citywide_risk_data, mock_cache
    ):
        """Test pagination for citywide risk data."""
        mock_get_cache.return_value = mock_cache
        
        mock_client = MagicMock()
        
        # Create separate mocks
        mock_main_query = MagicMock()
        mock_count_query = MagicMock()
        
        mock_main_response = MagicMock()
        mock_main_response.data = sample_citywide_risk_data[:2]
        mock_main_query.select.return_value = mock_main_query
        mock_main_query.order.return_value = mock_main_query
        mock_main_query.limit.return_value = mock_main_query
        mock_main_query.offset.return_value = mock_main_query
        mock_main_query.gte.return_value = mock_main_query
        mock_main_query.lte.return_value = mock_main_query
        mock_main_query.eq.return_value = mock_main_query
        mock_main_query.execute.return_value = mock_main_response
        
        mock_count_response = MagicMock()
        mock_count_response.count = 3  # Total count explicitly int
        mock_count_query.select.return_value = mock_count_query
        mock_count_query.gte.return_value = mock_count_query
        mock_count_query.lte.return_value = mock_count_query
        mock_count_query.eq.return_value = mock_count_query
        mock_count_query.execute.return_value = mock_count_response
        
        call_count = [0]
        def table_side_effect(table_name):
            call_count[0] += 1
            return mock_main_query if call_count[0] == 1 else mock_count_query
        
        mock_client.table.side_effect = table_side_effect
        mock_get_client.return_value = mock_client
        
        response = client.get("/api/v1/citywide-risk?limit=2&offset=0")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 2
        assert data["summary"]["pagination"]["limit"] == 2
    
    @patch("src.api.routes.citywide.get_cache")
    @patch("src.api.routes.citywide.get_supabase_client")
    def test_get_citywide_risk_uses_cache(
        self, mock_get_client, mock_get_cache, client, mock_cache, sample_citywide_risk_data
    ):
        """Test that citywide risk endpoint uses caching."""
        mock_get_cache.return_value = mock_cache
        
        mock_client = MagicMock()
        
        # Create separate mocks
        mock_main_query = MagicMock()
        mock_count_query = MagicMock()
        
        mock_main_response = MagicMock()
        mock_main_response.data = sample_citywide_risk_data
        mock_main_query.select.return_value = mock_main_query
        mock_main_query.order.return_value = mock_main_query
        mock_main_query.limit.return_value = mock_main_query
        mock_main_query.offset.return_value = mock_main_query
        mock_main_query.gte.return_value = mock_main_query
        mock_main_query.lte.return_value = mock_main_query
        mock_main_query.eq.return_value = mock_main_query
        mock_main_query.execute.return_value = mock_main_response
        
        mock_count_response = MagicMock()
        mock_count_response.count = 3  # Explicitly int
        mock_count_query.select.return_value = mock_count_query
        mock_count_query.gte.return_value = mock_count_query
        mock_count_query.lte.return_value = mock_count_query
        mock_count_query.eq.return_value = mock_count_query
        mock_count_query.execute.return_value = mock_count_response
        
        call_count = [0]
        def table_side_effect(table_name):
            call_count[0] += 1
            return mock_main_query if call_count[0] == 1 else mock_count_query
        
        mock_client.table.side_effect = table_side_effect
        mock_get_client.return_value = mock_client
        
        # First request
        response1 = client.get("/api/v1/citywide-risk")
        assert response1.status_code == status.HTTP_200_OK
        
        # Second request - should use cache
        response2 = client.get("/api/v1/citywide-risk")
        assert response2.status_code == status.HTTP_200_OK
        
        assert response1.json() == response2.json()
    
    @patch("src.api.routes.citywide.get_cache")
    @patch("src.api.routes.citywide.get_supabase_client")
    def test_get_citywide_risk_calculates_summary_statistics(
        self, mock_get_client, mock_get_cache, client, sample_citywide_risk_data, mock_cache
    ):
        """Test that summary statistics are correctly calculated."""
        mock_get_cache.return_value = mock_cache
        
        mock_client = MagicMock()
        
        # Create separate mocks
        mock_main_query = MagicMock()
        mock_count_query = MagicMock()
        
        mock_main_response = MagicMock()
        mock_main_response.data = sample_citywide_risk_data
        mock_main_query.select.return_value = mock_main_query
        mock_main_query.order.return_value = mock_main_query
        mock_main_query.limit.return_value = mock_main_query
        mock_main_query.offset.return_value = mock_main_query
        mock_main_query.gte.return_value = mock_main_query
        mock_main_query.lte.return_value = mock_main_query
        mock_main_query.eq.return_value = mock_main_query
        mock_main_query.execute.return_value = mock_main_response
        
        mock_count_response = MagicMock()
        mock_count_response.count = 3  # Explicitly int
        mock_count_query.select.return_value = mock_count_query
        mock_count_query.gte.return_value = mock_count_query
        mock_count_query.lte.return_value = mock_count_query
        mock_count_query.eq.return_value = mock_count_query
        mock_count_query.execute.return_value = mock_count_response
        
        call_count = [0]
        def table_side_effect(table_name):
            call_count[0] += 1
            return mock_main_query if call_count[0] == 1 else mock_count_query
        
        mock_client.table.side_effect = table_side_effect
        mock_get_client.return_value = mock_client
        
        response = client.get("/api/v1/citywide-risk")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        summary = data["summary"]
        
        assert summary["highest_risk_year"] == 2027
        assert summary["highest_risk_score"] == 88.7
        assert summary["critical_years"] == [2027]
        assert summary["high_risk_years"] == [2026]
        assert "average_risk_score" in summary
    
    @patch("src.api.routes.citywide.get_cache")
    @patch("src.api.routes.citywide.get_supabase_client")
    def test_get_citywide_risk_handles_empty_result(
        self, mock_get_client, mock_get_cache, client, mock_cache
    ):
        """Test endpoint when no data is found."""
        mock_get_cache.return_value = mock_cache
        
        mock_client = MagicMock()
        
        # Create separate mocks
        mock_main_query = MagicMock()
        mock_count_query = MagicMock()
        
        mock_main_response = MagicMock()
        mock_main_response.data = []
        mock_main_query.select.return_value = mock_main_query
        mock_main_query.order.return_value = mock_main_query
        mock_main_query.limit.return_value = mock_main_query
        mock_main_query.offset.return_value = mock_main_query
        mock_main_query.gte.return_value = mock_main_query
        mock_main_query.lte.return_value = mock_main_query
        mock_main_query.eq.return_value = mock_main_query
        mock_main_query.execute.return_value = mock_main_response
        
        mock_count_response = MagicMock()
        mock_count_response.count = 0  # Explicitly int
        mock_count_query.select.return_value = mock_count_query
        mock_count_query.gte.return_value = mock_count_query
        mock_count_query.lte.return_value = mock_count_query
        mock_count_query.eq.return_value = mock_count_query
        mock_count_query.execute.return_value = mock_count_response
        
        call_count = [0]
        def table_side_effect(table_name):
            call_count[0] += 1
            return mock_main_query if call_count[0] == 1 else mock_count_query
        
        mock_client.table.side_effect = table_side_effect
        mock_get_client.return_value = mock_client
        
        response = client.get("/api/v1/citywide-risk")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 0
        assert "No data available" in data["message"]
