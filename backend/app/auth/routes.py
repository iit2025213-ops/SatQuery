# app/auth/routes.py

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import logging

from app.auth.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, AuthResponse,
    RefreshTokenRequest, UserResponse, MessageResponse
)
from app.auth.jwt_handler import jwt_handler
from app.config import settings
from app.storage.supabase_client import SupabaseClient

logger = logging.getLogger("satquery")

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
security = HTTPBearer()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """
    Register new user
    
    - **email**: User email address
    - **password**: Password (min 8 characters)
    - **display_name**: Optional display name
    """
    try:
        # Get Supabase client from app state (will be injected)
        from app.main import supabase_client
        
        if not supabase_client:
            logger.error("Supabase client not initialized")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable"
            )
        
        # Create user in Supabase Auth
        try:
            auth_response = supabase_client.get_admin_client().auth.admin.create_user(
                {"email": request.email,
                "password": request.password,
                "email_confirm": True}  # Auto-confirm in development
            )
            user_id = auth_response.user.id
            
            logger.info(f"User registered: {request.email}")
        
        except Exception as e:
            if "already registered" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered"
                )
            logger.error(f"Supabase auth error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )
        
        # Create user profile in database
        try:
            supabase_client.get_admin_client().table("users").insert({
                "id": user_id,
                "email": request.email,
                "display_name": request.display_name
            }).execute()
            
            logger.info(f"User profile created: {user_id}")
        
        except Exception as e:
            logger.error(f"Failed to create user profile: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user profile"
            )
        
        # Generate tokens
        tokens = jwt_handler.create_token_pair(str(user_id), request.email)
        
        return AuthResponse(
            user=UserResponse(
                id=user_id,
                email=request.email,
                display_name=request.display_name,
                created_at=None,  # Will be set by database
                updated_at=None
            ),
            **tokens
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in register: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Login user with email and password
    
    Returns access and refresh tokens
    """
    try:
        from app.main import supabase_client
        
        if not supabase_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable"
            )
        
        # Authenticate with Supabase
        try:
            auth_response = supabase_client.get_user_client().auth.sign_in_with_password({
                "email": request.email,
                "password": request.password
            })
            
            user = auth_response.user
            user_id = user.id
            email = user.email
            
            logger.info(f"User logged in: {email}")
        
        except Exception as e:
            logger.warning(f"Login failed for {request.email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Get user profile
        try:
            user_data = supabase_client.get_user_client().table("users").select("*").eq("id", user_id).single().execute()
            user_profile = user_data.data
        except:
            user_profile = {"id": user_id, "email": email, "display_name": None}
        
        # Generate tokens
        tokens = jwt_handler.create_token_pair(str(user_id), email)
        
        return AuthResponse(
            user=UserResponse(
                id=user_id,
                email=email,
                display_name=user_profile.get("display_name"),
                created_at=user_profile.get("created_at"),
                updated_at=user_profile.get("updated_at")
            ),
            **tokens
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token
    """
    # Verify refresh token
    payload = jwt_handler.verify_token(request.refresh_token, token_type="refresh")
    
    if not payload:
        logger.warning("Invalid refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user_id = payload.get("sub")
    email = payload.get("email")
    
    # Create new access token
    access_token, expires_in = jwt_handler.create_access_token(user_id, email)
    
    logger.info(f"Token refreshed for user: {email}")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token,  # Return existing refresh token
        expires_in=expires_in
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get current authenticated user
    """
    from app.main import supabase_client
    
    # Extract user ID from token
    user_id = jwt_handler.get_user_id_from_token(credentials.credentials)
    email = jwt_handler.get_email_from_token(credentials.credentials)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    try:
        # Get user from database
        response = supabase_client.get_user_client().table("users").select("*").eq("id", user_id).single().execute()
        user_data = response.data
        
        return UserResponse(**user_data)
    
    except Exception as e:
        logger.error(f"Failed to get user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Logout user (token invalidation is handled client-side)
    
    Note: JWTs are stateless, so server-side logout just requires
    removing the token on the client. This endpoint is for logging
    the logout event.
    """
    email = jwt_handler.get_email_from_token(credentials.credentials)
    
    logger.info(f"User logged out: {email}")
    
    return MessageResponse(
        message="Successfully logged out",
        detail="Token has been invalidated on client"
    )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email():
    """
    Verify email (placeholder for future implementation)
    
    In production, this would handle email verification links
    """
    return MessageResponse(
        message="Email verification feature coming soon"
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password():
    """
    Reset password (placeholder for future implementation)
    
    In production, this would send a password reset email
    """
    return MessageResponse(
        message="Password reset feature coming soon"
    )
