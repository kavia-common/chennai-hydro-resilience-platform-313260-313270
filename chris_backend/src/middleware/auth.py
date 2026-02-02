"""
Authentication middleware for CHRIS Backend API.

Implements Supabase JWT verification for protected routes.
Validates Authorization: Bearer tokens and extracts user context.
"""
from fastapi import HTTPException, Security, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import logging
import os
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)

# Supabase JWT configuration
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")

# Extract project ref from Supabase URL for issuer validation
if SUPABASE_URL:
    # Format: https://projectref.supabase.co
    project_ref = SUPABASE_URL.replace("https://", "").replace(".supabase.co", "")
    EXPECTED_ISSUER = f"https://{project_ref}.supabase.co/auth/v1"
else:
    EXPECTED_ISSUER = None


async def verify_jwt_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[Dict[str, Any]]:
    """
    Verify Supabase JWT token from Authorization header.
    
    Args:
        credentials: HTTP Bearer credentials from request header
        
    Returns:
        Decoded JWT payload with user information, or None if no token
        
    Raises:
        HTTPException: If token is invalid, expired, or malformed
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    
    # Check if JWT secret is configured
    if not SUPABASE_JWT_SECRET:
        logger.error("SUPABASE_JWT_SECRET not configured. Cannot verify JWT tokens.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication is not properly configured on the server"
        )
    
    try:
        # Decode and verify JWT token
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": False  # Supabase tokens may not have 'aud'
            }
        )
        
        # Validate issuer if configured
        if EXPECTED_ISSUER and payload.get("iss") != EXPECTED_ISSUER:
            logger.warning(f"Invalid token issuer: {payload.get('iss')}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Extract user_id from sub claim
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Token missing 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token structure",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        logger.info(f"Successfully verified JWT for user: {user_id}")
        return payload
    
    except JWTError as e:
        logger.warning(f"JWT verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Unexpected error during JWT verification: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )


# PUBLIC_INTERFACE
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user (required).
    
    Use this dependency on routes that MUST have authentication.
    
    Args:
        credentials: HTTP Bearer credentials from request header
        
    Returns:
        User payload from JWT token
        
    Raises:
        HTTPException: If no token provided or token is invalid
    """
    if not credentials:
        logger.warning("No authorization credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    payload = await verify_jwt_token(credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return payload


# PUBLIC_INTERFACE
def require_auth(func):
    """
    Decorator to require authentication on route handlers.
    
    Usage:
    ```python
    @router.post("/protected-endpoint")
    @require_auth
    async def protected_route(user: Dict = Depends(get_current_user)):
        user_id = user["sub"]
        # ... protected logic
    ```
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Authentication is handled by get_current_user dependency
        return await func(*args, **kwargs)
    return wrapper


async def get_user_id_from_token(request: Request) -> Optional[str]:
    """
    Extract user_id from JWT token without raising exceptions.
    
    Useful for optional authentication scenarios where you want to
    scope queries to authenticated user if available.
    
    Args:
        request: FastAPI request object
        
    Returns:
        user_id (sub claim) if valid token present, None otherwise
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        if not SUPABASE_JWT_SECRET:
            return None
        
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_signature": True, "verify_exp": True}
        )
        
        return payload.get("sub")
    except Exception as e:
        logger.debug(f"Could not extract user_id from token: {str(e)}")
        return None
