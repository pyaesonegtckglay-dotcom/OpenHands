"""
Web client configuration endpoint.
Provides frontend with necessary configuration for UI rendering.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/web-client", tags=["Web Client Config"])


class LLMProvider(BaseModel):
    id: str
    name: str
    models: List[str]


class WebClientConfig(BaseModel):
    app_mode: str = "oss"  # "oss" or "saas"
    maintenance_start_time: Optional[str] = None
    faulty_models: Optional[List[str]] = None
    error_message: Optional[str] = None
    updated_at: Optional[str] = None
    user_consents_to_analytics: Optional[bool] = None
    is_new_user: bool = False
    available_providers: List[LLMProvider] = []
    default_provider: str = "anthropic"
    default_model: str = "claude-sonnet-4-20250514"


@router.get("/config", response_model=WebClientConfig)
async def get_web_client_config():
    """
    Get the web client configuration.
    
    Returns configuration needed by the frontend to render the UI properly,
    including app mode, available providers, and maintenance status.
    """
    # Return default config for now - can be extended with database values
    return WebClientConfig(
        app_mode="oss",
        available_providers=[
            LLMProvider(
                id="anthropic",
                name="Anthropic",
                models=["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"]
            ),
            LLMProvider(
                id="openai",
                name="OpenAI",
                models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
            ),
            LLMProvider(
                id="google",
                name="Google",
                models=["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
            ),
            LLMProvider(
                id="sambanova",
                name="SambaNova",
                models=["Meta-Llama-3.1-405B-Instruct", "Meta-Llama-3.1-70B-Instruct", "Meta-Llama-3.1-8B-Instruct"]
            ),
        ],
        default_provider="anthropic",
        default_model="claude-sonnet-4-20250514"
    )