# app/auth/jwt_handler.py

from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger("satquery")


class JWTHandler:
    """Handle JWT token creation and validation"""
    
    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_access_token_expire_minutes
        self.refresh_token_expire_days = settings.jwt_refresh_token_expire_days
    
    def create_access_token(self, user_id: str, email: str, expires_delta: Optional[timedelta] = None) -> tuple[str, int]:
        """
        Create JWT access token
        
        Returns:
            (token, expires_in_seconds)
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode = {
            "sub": user_id,
            "email": email,
            "type": "access",
            "iat": datetime.utcnow(),
            "exp": expire
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        expires_in = int((expire - datetime.utcnow()).total_seconds())
        
        logger.info(f"Created access token for user: {email}")
        
        return encoded_jwt, expires_in
    
    def create_refresh_token(self, user_id: str, email: str) -> tuple[str, int]:
        """
        Create JWT refresh token
        
        Returns:
            (token, expires_in_seconds)
        """
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode = {
            "sub": user_id,
            "email": email,
            "type": "refresh",
            "iat": datetime.utcnow(),
            "exp": expire
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        expires_in = int((expire - datetime.utcnow()).total_seconds())
        
        logger.info(f"Created refresh token for user: {email}")
        
        return encoded_jwt, expires_in
    
    def create_token_pair(self, user_id: str, email: str) -> dict:
        """Create both access and refresh tokens"""
        access_token, access_expires = self.create_access_token(user_id, email)
        refresh_token, refresh_expires = self.create_refresh_token(user_id, email)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": access_expires
        }
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[dict]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token string
            token_type: Expected token type ("access" or "refresh")
        
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Verify token type
            if payload.get("type") != token_type:
                logger.warning(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
                return None
            
            # Token is valid
            logger.debug(f"Token verified for user: {payload.get('email')}")
            return payload
        
        except JWTError as e:
            logger.warning(f"JWT verification failed: {str(e)}")
            return None
        
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {str(e)}")
            return None
    
    def get_user_id_from_token(self, token: str) -> Optional[str]:
        """Extract user ID from token"""
        payload = self.verify_token(token, token_type="access")
        if payload:
            return payload.get("sub")
        return None
    
    def get_email_from_token(self, token: str) -> Optional[str]:
        """Extract email from token"""
        payload = self.verify_token(token, token_type="access")
        if payload:
            return payload.get("email")
        return None
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            exp = payload.get("exp")
            if exp:
                return datetime.fromtimestamp(exp) < datetime.utcnow()
            return False
        except JWTError:
            return True


# Create global JWT handler instance
jwt_handler = JWTHandler()
