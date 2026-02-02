"""
Pydantic schemas for citywide risk aggregation endpoints.

These models define the response structure for overall city flood risk data.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from .forecast import CitywideRiskRecord


class CitywideRiskResponse(BaseModel):
    """
    Response schema for citywide risk endpoint.
    
    Returns all historical and predicted flood risk data for the city.
    """
    success: bool = Field(..., description="Whether the query was successful")
    data: List[CitywideRiskRecord] = Field(
        ...,
        description="List of citywide risk records ordered by year"
    )
    summary: Optional[dict] = Field(
        None,
        description="Aggregate statistics (e.g., highest risk year, average score)"
    )
    message: Optional[str] = Field(
        None,
        description="Additional information"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [
                    {
                        "year": 2025,
                        "risk_score": 65.5,
                        "risk_category": "Moderate",
                        "predicted_rainfall_mm": 1250.5
                    },
                    {
                        "year": 2027,
                        "risk_score": 88.7,
                        "risk_category": "Critical",
                        "predicted_rainfall_mm": 1650.8
                    }
                ],
                "summary": {
                    "highest_risk_year": 2027,
                    "average_risk_score": 65.5
                },
                "message": None
            }
        }
