"""
Security logging utility for CHRIS Backend API.

Provides structured logging for authentication failures, rate limit violations,
and other security-relevant events.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import json

# Create dedicated security logger
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.INFO)

# Add handler if not already configured
if not security_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    security_logger.addHandler(handler)


def log_auth_failure(
    reason: str,
    client_ip: str,
    endpoint: str,
    user_id: Optional[str] = None,
    additional_info: Optional[Dict[str, Any]] = None
):
    """
    Log authentication failure event.
    
    Args:
        reason: Reason for authentication failure
        client_ip: Client IP address
        endpoint: Endpoint being accessed
        user_id: User ID if available from token
        additional_info: Additional context
    """
    event = {
        "event_type": "auth_failure",
        "timestamp": datetime.utcnow().isoformat(),
        "reason": reason,
        "client_ip": client_ip,
        "endpoint": endpoint,
        "user_id": user_id,
        "additional_info": additional_info or {}
    }
    
    security_logger.warning(f"AUTH_FAILURE: {json.dumps(event)}")


def log_rate_limit_exceeded(
    client_ip: str,
    endpoint: str,
    request_count: int,
    window_seconds: int
):
    """
    Log rate limit violation event.
    
    Args:
        client_ip: Client IP address
        endpoint: Endpoint being accessed
        request_count: Number of requests in window
        window_seconds: Rate limit window duration
    """
    event = {
        "event_type": "rate_limit_exceeded",
        "timestamp": datetime.utcnow().isoformat(),
        "client_ip": client_ip,
        "endpoint": endpoint,
        "request_count": request_count,
        "window_seconds": window_seconds
    }
    
    security_logger.warning(f"RATE_LIMIT: {json.dumps(event)}")


def log_suspicious_activity(
    activity_type: str,
    client_ip: str,
    details: Dict[str, Any]
):
    """
    Log suspicious activity event.
    
    Args:
        activity_type: Type of suspicious activity
        client_ip: Client IP address
        details: Additional details about the activity
    """
    event = {
        "event_type": "suspicious_activity",
        "timestamp": datetime.utcnow().isoformat(),
        "activity_type": activity_type,
        "client_ip": client_ip,
        "details": details
    }
    
    security_logger.warning(f"SUSPICIOUS: {json.dumps(event)}")


def log_auth_success(
    user_id: str,
    client_ip: str,
    endpoint: str
):
    """
    Log successful authentication event.
    
    Args:
        user_id: Authenticated user ID
        client_ip: Client IP address
        endpoint: Endpoint being accessed
    """
    event = {
        "event_type": "auth_success",
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "client_ip": client_ip,
        "endpoint": endpoint
    }
    
    security_logger.info(f"AUTH_SUCCESS: {json.dumps(event)}")
