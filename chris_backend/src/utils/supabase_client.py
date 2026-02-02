"""
Supabase client utility for CHRIS backend.

This module initializes the Supabase client using environment variables
and provides a singleton instance for database operations with optimized queries.
"""
import os
from supabase import create_client, Client
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Initialize and return Supabase client singleton.
    
    Ensures client reuse for connection pooling and efficiency.
    
    Returns:
        Client: Supabase client instance
        
    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY environment variables are not set
    """
    global _supabase_client
    
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY environment variables must be set. "
                "Please configure these in your .env file."
            )
        
        _supabase_client = create_client(url, key)
        logger.info("Supabase client initialized (singleton)")
    
    return _supabase_client


# PUBLIC_INTERFACE
def build_optimized_query(
    table_name: str,
    select_fields: List[str] = None,
    filters: dict = None,
    order_by: str = None,
    order_desc: bool = False,
    limit: int = None,
    offset: int = None
):
    """
    Build optimized Supabase query with proper select filters and limits.
    
    Best practices:
    - Always specify select fields instead of using '*' when possible
    - Apply filters before ordering for better query planning
    - Use limits to reduce data transfer
    - Add proper indexes in database for filtered/ordered columns
    
    Usage:
    ```python
    query = build_optimized_query(
        table_name="citywide_risk",
        select_fields=["year", "risk_score", "risk_category"],
        filters={"risk_category": "High"},
        order_by="year",
        limit=50
    )
    response = query.execute()
    ```
    
    Args:
        table_name: Name of the table
        select_fields: List of fields to select (None = all fields)
        filters: Dictionary of field:value filters (equality only)
        order_by: Field to order by
        order_desc: Order descending if True
        limit: Maximum results to return
        offset: Number of results to skip
        
    Returns:
        Configured Supabase query builder
        
    Note:
        Recommended database indexes:
        - citywide_risk: INDEX on (year, risk_category, risk_score)
        - zone_risk: INDEX on (zone_id, capacity_category)
    """
    client = get_supabase_client()
    
    # Select fields
    select_clause = "*" if not select_fields else ", ".join(select_fields)
    query = client.table(table_name).select(select_clause)
    
    # Apply filters (equality only for safety)
    if filters:
        for field, value in filters.items():
            if value is not None:
                query = query.eq(field, value)
    
    # Apply ordering
    if order_by:
        query = query.order(order_by, desc=order_desc)
    
    # Apply pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)
    
    return query


# Export singleton instance (lazy initialization)
supabase = None  # Will be initialized on first use via get_supabase_client()
