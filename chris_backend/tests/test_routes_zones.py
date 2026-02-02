"""
Tests for sponge zones API routes.

Tests the spatial U-Net-based zone mapping endpoints.
"""
from fastapi import status
from unittest.mock import patch, MagicMock


class TestSpongeZonesEndpoint:
    """Tests for GET /api/v1/map/sponge-zones endpoint."""
    
    @patch("src.api.routes.zones.get_supabase_client")
    @patch("src.api.routes.zones.get_cache")
    def test_get_sponge_zones_returns_geojson(
        self, mock_get_cache, mock_get_client, client, sample_zone_data, mock_cache
    ):
        """Test that sponge zones endpoint returns GeoJSON FeatureCollection."""
        # Mock cache to return None (cache miss)
        mock_get_cache.return_value = mock_cache
        mock_cache.get.return_value = None
        
        # Mock Supabase client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Create a single mock query that handles both main and count queries
        mock_query = MagicMock()
        
        # Mock main response
        mock_main_response = MagicMock()
        mock_main_response.data = sample_zone_data
        mock_main_response.count = len(sample_zone_data)
        
        # Setup chaining methods
        mock_query.select.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = mock_main_response
        
        mock_client.table.return_value = mock_query
        
        response = client.get("/api/v1/map/sponge-zones")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 2
        assert "metadata" in data
        assert data["metadata"]["total_zones"] == 2
    
    @patch("src.api.routes.zones.get_cache")
    @patch("src.api.routes.zones.get_supabase_client")
    def test_get_sponge_zones_uses_cache(
        self, mock_get_client, mock_get_cache, client, mock_cache, sample_zone_data
    ):
        """Test that sponge zones endpoint uses caching."""
        mock_get_cache.return_value = mock_cache
        
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_query = MagicMock()
        mock_response = MagicMock()
        mock_response.data = sample_zone_data
        mock_response.count = len(sample_zone_data)
        
        mock_query.select.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = mock_response
        
        mock_client.table.return_value = mock_query
        
        # First request - should hit database
        response1 = client.get("/api/v1/map/sponge-zones")
        assert response1.status_code == status.HTTP_200_OK
        
        # Second request - should hit cache
        response2 = client.get("/api/v1/map/sponge-zones")
        assert response2.status_code == status.HTTP_200_OK
        
        # Verify data is same
        assert response1.json() == response2.json()
    
    @patch("src.api.routes.zones.get_cache")
    @patch("src.api.routes.zones.get_supabase_client")
    def test_get_sponge_zones_filters_by_capacity(
        self, mock_get_client, mock_get_cache, client, sample_zone_data, mock_cache
    ):
        """Test filtering sponge zones by capacity category."""
        mock_get_cache.return_value = mock_cache
        mock_cache.get.return_value = None
        
        # Mock Supabase response with only High capacity zones
        filtered_data = [z for z in sample_zone_data if z["capacity_category"] == "High"]
        
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_query = MagicMock()
        mock_response = MagicMock()
        mock_response.data = filtered_data
        mock_response.count = len(filtered_data)
        
        mock_query.select.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = mock_response
        
        mock_client.table.return_value = mock_query
        
        response = client.get("/api/v1/map/sponge-zones?capacity_category=High")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["features"]) == 1
        assert data["features"][0]["properties"]["capacity_category"] == "High"
    
    def test_get_sponge_zones_validates_capacity_category(self, client):
        """Test that invalid capacity category is rejected."""
        response = client.get("/api/v1/map/sponge-zones?capacity_category=Invalid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch("src.api.routes.zones.get_cache")
    @patch("src.api.routes.zones.get_supabase_client")
    def test_get_sponge_zones_pagination(
        self, mock_get_client, mock_get_cache, client, sample_zone_data, mock_cache
    ):
        """Test pagination parameters for sponge zones."""
        mock_get_cache.return_value = mock_cache
        mock_cache.get.return_value = None
        
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_query = MagicMock()
        mock_response = MagicMock()
        mock_response.data = sample_zone_data[:1]
        mock_response.count = len(sample_zone_data)
        
        mock_query.select.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = mock_response
        
        mock_client.table.return_value = mock_query
        
        response = client.get("/api/v1/map/sponge-zones?limit=1&offset=0")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["features"]) == 1
        assert data["metadata"]["pagination"]["limit"] == 1
        assert data["metadata"]["pagination"]["has_more"] is True
    
    def test_get_sponge_zones_validates_pagination_bounds(self, client):
        """Test that pagination parameters are validated."""
        # Test limit too high
        response = client.get("/api/v1/map/sponge-zones?limit=1000")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test negative offset
        response = client.get("/api/v1/map/sponge-zones?offset=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch("src.api.routes.zones.get_cache")
    @patch("src.api.routes.zones.get_supabase_client")
    def test_get_sponge_zones_handles_empty_result(
        self, mock_get_client, mock_get_cache, client, mock_cache
    ):
        """Test endpoint when no zones are found."""
        mock_get_cache.return_value = mock_cache
        mock_cache.get.return_value = None
        
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_query = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_response.count = 0
        
        mock_query.select.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = mock_response
        
        mock_client.table.return_value = mock_query
        
        response = client.get("/api/v1/map/sponge-zones")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 0
        assert "No zones found" in data["metadata"]["message"]


class TestZoneDetailsEndpoint:
    """Tests for GET /api/v1/zone-details endpoint."""
    
    @patch("src.api.routes.zones.get_cache")
    @patch("src.api.routes.zones.get_supabase_client")
    def test_get_zone_details_returns_single_zone(
        self, mock_get_client, mock_get_cache, client, sample_zone_data, mock_cache
    ):
        """Test retrieving details for a specific zone."""
        mock_get_cache.return_value = mock_cache
        mock_cache.get.return_value = None
        
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_query = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [sample_zone_data[0]]
        mock_query.execute.return_value = mock_response
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_client.table.return_value = mock_query
        
        response = client.get("/api/v1/zone-details?zone_id=Z001")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "Z001"
        assert data["data"]["properties"]["zone_name"] == "Adyar River Basin Zone 4"
    
    @patch("src.api.routes.zones.get_cache")
    @patch("src.api.routes.zones.get_supabase_client")
    def test_get_zone_details_not_found(
        self, mock_get_client, mock_get_cache, client, mock_cache
    ):
        """Test zone details when zone doesn't exist."""
        mock_get_cache.return_value = mock_cache
        mock_cache.get.return_value = None
        
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_query = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_query.execute.return_value = mock_response
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_client.table.return_value = mock_query
        
        response = client.get("/api/v1/zone-details?zone_id=NONEXISTENT")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]
    
    def test_get_zone_details_validates_zone_id(self, client):
        """Test that zone_id is validated for security."""
        # Test with SQL injection attempt
        response = client.get("/api/v1/zone-details?zone_id=Z001'; DROP TABLE users--")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test with XSS attempt
        response = client.get("/api/v1/zone-details?zone_id=<script>alert('xss')</script>")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_get_zone_details_requires_zone_id(self, client):
        """Test that zone_id parameter is required."""
        response = client.get("/api/v1/zone-details")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch("src.api.routes.zones.get_cache")
    @patch("src.api.routes.zones.get_supabase_client")
    def test_get_zone_details_uses_cache(
        self, mock_get_client, mock_get_cache, client, mock_cache, sample_zone_data
    ):
        """Test that zone details endpoint uses caching."""
        mock_get_cache.return_value = mock_cache
        
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [sample_zone_data[0]]
        
        mock_table.execute.return_value = mock_response
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client
        
        # First request
        response1 = client.get("/api/v1/zone-details?zone_id=Z001")
        assert response1.status_code == status.HTTP_200_OK
        
        # Second request - should use cache
        response2 = client.get("/api/v1/zone-details?zone_id=Z001")
        assert response2.status_code == status.HTTP_200_OK
        
        assert response1.json() == response2.json()
