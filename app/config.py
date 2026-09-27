"""SatQuery AI — Application configuration."""

from __future__ import annotations
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application-wide settings loaded from environment / .env file."""

    # --- LLM ---
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="", description="OpenAI model name")
    openai_base_url: str = Field(
        default="", description="Custom OpenAI-compatible endpoint (empty = official)"
    )
    openai_temperature: float = Field(
        default=0.1, ge=0.0, le=2.0, description="LLM temperature for decisions"
    )
    openai_max_retries: int = Field(
        default=2, ge=0, description="Max retries for OpenAI API calls"
    )
    openai_max_tokens_decide: int = Field(
        default=2000, ge=1, description="Max output tokens for decide() calls"
    )
    openai_max_tokens_synthesize: int = Field(
        default=1200, ge=1, description="Max output tokens for synthesize() calls"
    )

    # --- Agent limits ---
    max_steps: int = Field(default=25, ge=1, description="Maximum agent loop steps")
    max_replans: int = Field(default=3, ge=0, description="Maximum replanning attempts")
    max_retries_per_task: int = Field(
        default=2, ge=0, description="Maximum retries per failed capability"
    )

    # --- Specialist model endpoints ---
    # GeoChat (VLM: scene interpretation, VQA, captioning, grounding)
    geochat_endpoint: str = Field(default="", description="GeoChat inference endpoint URL")
    geochat_api_key: str = Field(default="", description="GeoChat API key")
    geochat_timeout_seconds: int = Field(default=1200, ge=1, description="GeoChat request timeout")
   

    # Change Detection (bi-temporal change detection)
    change_detection_endpoint: str = Field(default="", description="Change Detection inference endpoint URL")
    change_detection_api_key: str = Field(default="", description="Change Detection API key")
    change_detection_timeout_seconds: float = Field(default=600, ge=1, description="Change Detection request timeout")

    # Prithvi / SARMAE (retired — kept for env-var backward compatibility)
    prithvi_endpoint: str = Field(default="", description="[RETIRED] Prithvi endpoint")
    prithvi_api_key: str = Field(default="", description="[RETIRED] Prithvi API key")
    prithvi_timeout_seconds: int = Field(default=1200, ge=1, description="[RETIRED]")

    sarmae_endpoint: str = Field(default="", description="[RETIRED] SARMAE endpoint")
    sarmae_api_key: str = Field(default="", description="[RETIRED] SARMAE API key")
    sarmae_timeout_seconds: int = Field(default=1200, ge=1, description="[RETIRED]")

    # TerraMind (multimodal EO)
    terramind_endpoint: str = Field(default="", description="TerraMind inference endpoint URL")
    terramind_api_key: str = Field(default="", description="TerraMind API key")
    terramind_timeout_seconds: int = Field(default=1200, ge=1, description="TerraMind request timeout")

    # --- Cloudinary ---
    cloudinary_cloud_name: str = Field(default="", description="Cloudinary cloud name")
    cloudinary_api_key: str = Field(default="", description="Cloudinary API key")
    cloudinary_api_secret: str = Field(default="", description="Cloudinary API secret")
    cloudinary_upload_folder: str = Field(default="satquery-ai", description="Cloudinary folder")
    cloudinary_upload_preset: str = Field(default="Satquery", description="Cloudinary preset")

    # --- Logging ---
    log_level: str = Field(default="INFO", description="Logging level")

    # --- API ---
    cors_origins: str = Field(default="*", description="Comma-separated list of allowed CORS origins")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    """Factory that returns a cached Settings instance."""
    return Settings()
