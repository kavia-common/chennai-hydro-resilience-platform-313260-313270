"""
Tests for authentication middleware.

Tests JWT verification, token validation, and user context extraction.
"""
import pytest
from fastapi import status, HTTPException
from jose import jwt
from datetime import datetime, timedelta
import os


class TestJWTVerification:
    """Tests for JWT token verification."""
    
    @pytest.mark.asyncio
    async def test_verify_jwt_token_with_valid_token(self, mock_jwt_token):
        """Test JWT verification with a valid token."""
        from src.middleware.auth import verify_jwt_token
        from fastapi.security import HTTPAuthorizationCredentials
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=mock_jwt_token
        )
        
        payload = await verify_jwt_token(credentials)
        
        assert payload is not None
        assert payload["sub"] == "test-user-123"
        assert payload["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_verify_jwt_token_with_no_credentials(self):
        """Test JWT verification when no credentials provided."""
        from src.middleware.auth import verify_jwt_token
        
        payload = await verify_jwt_token(None)
        assert payload is None
    
    @pytest.mark.asyncio
    async def test_verify_jwt_token_with_invalid_signature(self):
        """Test JWT verification with invalid signature."""
        from src.middleware.auth import verify_jwt_token
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Create token with wrong secret
        payload = {
            "sub": "test-user-123",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        invalid_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=invalid_token
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_token(credentials)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_verify_jwt_token_with_expired_token(self):
        """Test JWT verification with expired token."""
        from src.middleware.auth import verify_jwt_token
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Create expired token
        payload = {
            "sub": "test-user-123",
            "iat": datetime.utcnow() - timedelta(hours=2),
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        expired_token = jwt.encode(
            payload,
            os.environ["SUPABASE_JWT_SECRET"],
            algorithm="HS256"
        )
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=expired_token
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_token(credentials)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "expired" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_verify_jwt_token_with_missing_sub_claim(self):
        """Test JWT verification when sub claim is missing."""
        from src.middleware.auth import verify_jwt_token
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Create token without sub claim
        payload = {
            "email": "test@example.com",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(
            payload,
            os.environ["SUPABASE_JWT_SECRET"],
            algorithm="HS256"
        )
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_token(credentials)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_token(self, mock_jwt_token):
        """Test get_current_user with valid credentials."""
        from src.middleware.auth import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=mock_jwt_token
        )
        
        user = await get_current_user(credentials)
        
        assert user is not None
        assert user["sub"] == "test-user-123"
    
    @pytest.mark.asyncio
    async def test_get_current_user_without_credentials(self):
        """Test get_current_user when no credentials provided."""
        from src.middleware.auth import get_current_user
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication required" in exc_info.value.detail


class TestGetUserIdFromToken:
    """Tests for optional user ID extraction."""
    
    @pytest.mark.asyncio
    async def test_get_user_id_from_token_with_valid_token(self, mock_jwt_token):
        """Test extracting user ID from valid token."""
        from src.middleware.auth import get_user_id_from_token
        
        # Create mock request with Authorization header
        mock_request = type('Request', (), {
            'headers': {'Authorization': f'Bearer {mock_jwt_token}'}
        })()
        
        user_id = await get_user_id_from_token(mock_request)
        
        assert user_id == "test-user-123"
    
    @pytest.mark.asyncio
    async def test_get_user_id_from_token_without_header(self):
        """Test extracting user ID when no auth header present."""
        from src.middleware.auth import get_user_id_from_token
        
        mock_request = type('Request', (), {'headers': {}})()
        
        user_id = await get_user_id_from_token(mock_request)
        
        assert user_id is None
    
    @pytest.mark.asyncio
    async def test_get_user_id_from_token_with_invalid_token(self):
        """Test extracting user ID from invalid token."""
        from src.middleware.auth import get_user_id_from_token
        
        mock_request = type('Request', (), {
            'headers': {'Authorization': 'Bearer invalid-token'}
        })()
        
        user_id = await get_user_id_from_token(mock_request)
        
        assert user_id is None
