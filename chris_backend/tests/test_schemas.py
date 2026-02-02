"""
Tests for Pydantic schemas and validation.

Tests data validation, serialization, and schema constraints.
"""
import pytest
from pydantic import ValidationError


class TestForecastSchemas:
    """Tests for forecast-related schemas."""
    
    def test_forecast_request_valid(self):
        """Test valid ForecastRequest."""
        from src.schemas.forecast import ForecastRequest
        
        request = ForecastRequest(years=5, include_climate_factors=True)
        
        assert request.years == 5
        assert request.include_climate_factors is True
    
    def test_forecast_request_validates_years_range(self):
        """Test that years parameter is validated."""
        from src.schemas.forecast import ForecastRequest
        
        # Test years < 1
        with pytest.raises(ValidationError):
            ForecastRequest(years=0)
        
        # Test years > 10
        with pytest.raises(ValidationError):
            ForecastRequest(years=11)
    
    def test_forecast_request_defaults(self):
        """Test default values for ForecastRequest."""
        from src.schemas.forecast import ForecastRequest
        
        request = ForecastRequest()
        
        assert request.years == 5
        assert request.include_climate_factors is True
    
    def test_citywide_risk_record_valid(self):
        """Test valid CitywideRiskRecord."""
        from src.schemas.forecast import CitywideRiskRecord
        
        record = CitywideRiskRecord(
            year=2025,
            risk_score=65.5,
            risk_category="Moderate",
            oni_anomaly=0.5,
            iod_anomaly=0.3,
            predicted_rainfall_mm=1250.5,
            confidence=0.82
        )
        
        assert record.year == 2025
        assert record.risk_score == 65.5
        assert record.risk_category == "Moderate"
    
    def test_citywide_risk_record_validates_category(self):
        """Test risk category validation."""
        from src.schemas.forecast import CitywideRiskRecord
        
        with pytest.raises(ValidationError):
            CitywideRiskRecord(
                year=2025,
                risk_score=65.5,
                risk_category="Invalid"
            )
    
    def test_citywide_risk_record_validates_ranges(self):
        """Test numeric range validation."""
        from src.schemas.forecast import CitywideRiskRecord
        
        # Test risk_score > 100
        with pytest.raises(ValidationError):
            CitywideRiskRecord(
                year=2025,
                risk_score=150.0,
                risk_category="High"
            )
        
        # Test confidence > 1
        with pytest.raises(ValidationError):
            CitywideRiskRecord(
                year=2025,
                risk_score=65.5,
                risk_category="Moderate",
                confidence=1.5
            )


class TestZoneSchemas:
    """Tests for zone-related schemas."""
    
    def test_zone_properties_valid(self):
        """Test valid ZoneProperties."""
        from src.schemas.zone import ZoneProperties
        
        props = ZoneProperties(
            zone_id="Z001",
            zone_name="Test Zone",
            capacity_score=85.2,
            capacity_category="High",
            mndwi=0.65,
            ndvi=0.25
        )
        
        assert props.zone_id == "Z001"
        assert props.capacity_category == "High"
    
    def test_zone_properties_validates_zone_id(self):
        """Test zone_id validation against injection."""
        from src.schemas.zone import ZoneProperties
        
        # Valid zone_id
        props = ZoneProperties(
            zone_id="Z001",
            zone_name="Test",
            capacity_score=50.0,
            capacity_category="Moderate"
        )
        assert props.zone_id == "Z001"
        
        # Invalid zone_id with special characters
        with pytest.raises(ValidationError):
            ZoneProperties(
                zone_id="Z001'; DROP TABLE--",
                zone_name="Test",
                capacity_score=50.0,
                capacity_category="Moderate"
            )
    
    def test_sponge_zone_feature_geojson_structure(self):
        """Test GeoJSON Feature structure."""
        from src.schemas.zone import SpongeZoneFeature, ZoneProperties
        
        props = ZoneProperties(
            zone_id="Z001",
            zone_name="Test Zone",
            capacity_score=85.2,
            capacity_category="High"
        )
        
        feature = SpongeZoneFeature(
            id="Z001",
            geometry={
                "type": "Polygon",
                "coordinates": [[[80.27, 13.00], [80.28, 13.00], [80.27, 13.00]]]
            },
            properties=props
        )
        
        assert feature.type == "Feature"
        assert feature.id == "Z001"
        assert feature.geometry["type"] == "Polygon"
    
    def test_sponge_zone_collection_structure(self):
        """Test GeoJSON FeatureCollection structure."""
        from src.schemas.zone import SpongeZoneCollection
        
        collection = SpongeZoneCollection(
            features=[],
            metadata={"total_zones": 0}
        )
        
        assert collection.type == "FeatureCollection"
        assert len(collection.features) == 0


class TestCitywideSchemas:
    """Tests for citywide risk schemas."""
    
    def test_citywide_risk_response_validates_order(self):
        """Test that data must be ordered by year."""
        from src.schemas.citywide import CitywideRiskResponse
        from src.schemas.forecast import CitywideRiskRecord
        
        # Valid ordered data
        records = [
            CitywideRiskRecord(year=2025, risk_score=65.5, risk_category="Moderate"),
            CitywideRiskRecord(year=2026, risk_score=72.3, risk_category="High")
        ]
        
        response = CitywideRiskResponse(
            success=True,
            data=records,
            summary={}
        )
        
        assert len(response.data) == 2
        
        # Invalid unordered data
        unordered_records = [
            CitywideRiskRecord(year=2026, risk_score=72.3, risk_category="High"),
            CitywideRiskRecord(year=2025, risk_score=65.5, risk_category="Moderate")
        ]
        
        with pytest.raises(ValidationError):
            CitywideRiskResponse(
                success=True,
                data=unordered_records,
                summary={}
            )
