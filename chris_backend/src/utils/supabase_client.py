"""
Supabase client utility for CHRIS backend.

This module initializes the Supabase client using environment variables
and provides a singleton instance for database operations.
"""
import os
from supabase import create_client, Client
from typing import Optional


_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Initialize and return Supabase client singleton.
    
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
    
    return _supabase_client


# Export singleton instance
supabase = None  # Will be initialized on first use via get_supabase_client()
