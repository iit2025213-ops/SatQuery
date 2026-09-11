# app/auth/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

from app.auth.jwt_handler import jwt_handler
from app.storage.supabase_client import SupabaseClient

logger = logging.getLogger("satquery")

# HTTP Bearer scheme for Swagger docs
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract and validate user ID from JWT token
    
    Used as dependency for protected endpoints
    """
    token = credentials.credentials
    
    user_id = jwt_handler.get_user_id_from_token(token)
    
    if not user_id:
        logger.warning("Failed to extract user ID from token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    supabase: SupabaseClient = Depends(lambda: None)  # Will be injected from app state
) -> dict:
    """
    Get current authenticated user from database
    
    Used when full user object is needed
    """
    # This will be called with supabase client from app state
    # For now, return user_id and email from token
    email = jwt_handler.get_email_from_token  # Get from token directly
    
    return {
        "id": user_id,
        "email": email
    }


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Optionally extract user ID if token provided
    
    Used for endpoints that work with or without auth
    """
    if not credentials:
        return None
    
    user_id = jwt_handler.get_user_id_from_token(credentials.credentials)
    return user_id


class ProtectedRoute:
    """Decorator for protected routes"""
    
    @staticmethod
    def require_auth(func):
        """Decorator to require authentication"""
        async def wrapper(*args, user_id: str = Depends(get_current_user_id), **kwargs):
            # user_id is guaranteed to be valid
            kwargs['user_id'] = user_id
            return await func(*args, **kwargs)
        return wrapper
