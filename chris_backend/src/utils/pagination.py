"""
Pagination utility for CHRIS Backend API.

Provides cursor-based and offset-based pagination for efficient
handling of large result sets.
"""
from typing import TypeVar, Generic, List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class PaginationParams(BaseModel):
    """
    Standard pagination parameters.
    
    Supports both offset-based and limit-based pagination.
    """
    
    limit: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of items to return (1-1000)"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip"
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.
    
    Includes pagination metadata and data.
    """
    
    success: bool = Field(default=True, description="Success status")
    data: List[T] = Field(description="Paginated data items")
    pagination: Dict[str, Any] = Field(description="Pagination metadata")
    message: Optional[str] = Field(default=None, description="Optional message")


# PUBLIC_INTERFACE
def paginate_results(
    data: List[T],
    limit: int,
    offset: int,
    total_count: Optional[int] = None
) -> Dict[str, Any]:
    """
    Apply pagination to results and generate metadata.
    
    Args:
        data: Full dataset or paginated subset
        limit: Items per page
        offset: Starting offset
        total_count: Total count (if known, for better metadata)
        
    Returns:
        Dictionary with paginated data and metadata
    """
    # If total_count not provided, use data length
    if total_count is None:
        total_count = len(data)
    
    # Defensive check: coerce total_count to int if it's not
    # This handles cases where mock objects or other types are passed
    if not isinstance(total_count, int):
        try:
            total_count = int(total_count)
        except (TypeError, ValueError):
            logger.warning(f"Invalid total_count type: {type(total_count)}, defaulting to data length")
            total_count = len(data)
    
    # Apply pagination to data
    paginated_data = data[offset:offset + limit]
    
    # Calculate pagination metadata
    has_more = (offset + limit) < total_count
    next_offset = offset + limit if has_more else None
    prev_offset = max(0, offset - limit) if offset > 0 else None
    
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 0
    current_page = (offset // limit) + 1 if limit > 0 else 1
    
    pagination_meta = {
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "current_page": current_page,
        "total_pages": total_pages,
        "has_more": has_more,
        "next_offset": next_offset,
        "prev_offset": prev_offset,
        "returned_count": len(paginated_data)
    }
    
    logger.debug(
        f"Paginated results: offset={offset}, limit={limit}, "
        f"total={total_count}, returned={len(paginated_data)}"
    )
    
    return {
        "data": paginated_data,
        "pagination": pagination_meta
    }


# PUBLIC_INTERFACE
def build_supabase_pagination_query(query, limit: int, offset: int):
    """
    Apply pagination to Supabase query.
    
    Usage:
    ```python
    query = supabase.table("citywide_risk").select("*")
    query = build_supabase_pagination_query(query, limit=50, offset=0)
    response = query.execute()
    ```
    
    Args:
        query: Supabase query builder
        limit: Items per page
        offset: Starting offset
        
    Returns:
        Query with pagination applied
    """
    return query.limit(limit).offset(offset)


# PUBLIC_INTERFACE
def validate_pagination_params(limit: int, offset: int) -> tuple[int, int]:
    """
    Validate and normalize pagination parameters.
    
    Args:
        limit: Requested limit
        offset: Requested offset
        
    Returns:
        Tuple of (validated_limit, validated_offset)
    """
    # Ensure limit is within bounds
    limit = max(1, min(limit, 1000))
    
    # Ensure offset is non-negative
    offset = max(0, offset)
    
    return limit, offset
