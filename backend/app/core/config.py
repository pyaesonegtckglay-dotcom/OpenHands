"""
Core configuration for ManusAI backend.
ALL secrets are loaded exclusively from environment variables.
Never hardcode secrets in source code.
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "ManusAI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    CORS_ORIGINS: list = ["*"]

    # Database — set DATABASE_URL on Render
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Redis — set REDIS_URL on Render
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # E2B Sandbox — set E2B_API_KEY on Render
    E2B_API_KEY: str = os.getenv("E2B_API_KEY", "")

    # Supabase — set SUPABASE_URL / SUPABASE_KEY on Render
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # AI Provider Keys — set on Render (comma-separated)
    # GEMINI_API_KEYS=key1,key2,key3
    # GITHUB_MODELS_TOKENS=token1,token2
    # SAMBANOVA_API_KEYS=key1,key2
    GEMINI_API_KEYS: str = os.getenv("GEMINI_API_KEYS", "")
    GITHUB_MODELS_TOKENS: str = os.getenv("GITHUB_MODELS_TOKENS", "")
    SAMBANOVA_API_KEYS: str = os.getenv("SAMBANOVA_API_KEYS", "")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
