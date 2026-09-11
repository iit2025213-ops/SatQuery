# app/config.py

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Global application settings from environment variables"""
    
    # App
    app_name: str = "SatQuery AI"
    app_version: str = "0.1.0"
    backend_url: str
    backend_port: int = 8000
    debug: bool = False
    
    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_service_role_key: str
    supabase_db_url: Optional[str] = None  # For direct connection if needed
    
    # Cloudinary
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str
    cloudinary_upload_folder: str = "satquery-ai"
    
    # JWT
    jwt_secret_key: str  # Min 32 characters
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    
    # AI Brain
    ai_brain_url: str  # ws://your-server:8000/brain
    ai_brain_timeout_seconds: int = 30
    
    # OpenAI (for future LLM integration)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4.1-mini"
    
    # Google Earth Engine
    gee_service_account_key_path: Optional[str] = None  # Path to service account JSON
    gee_project_id: Optional[str] = None  # GEE cloud project ID
    
    # Agent Limits
    max_agent_steps: int = 20
    max_replans: int = 3
    max_retries_per_task: int = 2
    max_execution_time_seconds: int = 3600  # 1 hour
    
    # CORS
    cors_origins: list = ["http://localhost:3000", "http://localhost:8080"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list = ["*"]
    cors_allow_headers: list = ["*"]
    
    # Logging
    log_level: str = "INFO"
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period_seconds: int = 3600
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Allow extra environment variables
        extra = "allow"

# Create global settings instance
settings = Settings()
