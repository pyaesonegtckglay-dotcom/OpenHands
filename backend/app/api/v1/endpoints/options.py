"""
Options endpoints for frontend compatibility.
Provides models and security analyzers configuration.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/options", tags=["Options"])


class ModelProvider(BaseModel):
    name: str
    slug: str
    models: List[str]
    is_verified: bool = True


class ModelsResponse(BaseModel):
    providers: List[ModelProvider] = []
    default_provider: str = "anthropic"
    default_model: str = "claude-sonnet-4-20250514"


@router.get("/models", response_model=ModelsResponse)
async def get_models():
    """
    Get available LLM models from verified providers.
    """
    return ModelsResponse(
        providers=[
            ModelProvider(
                name="Anthropic",
                slug="anthropic",
                models=["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
                is_verified=True
            ),
            ModelProvider(
                name="OpenAI",
                slug="openai",
                models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
                is_verified=True
            ),
            ModelProvider(
                name="Google",
                slug="google",
                models=["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
                is_verified=True
            ),
            ModelProvider(
                name="SambaNova",
                slug="sambanova",
                models=["Meta-Llama-3.1-405B-Instruct", "Meta-Llama-3.1-70B-Instruct", "Meta-Llama-3.1-8B-Instruct"],
                is_verified=True
            ),
        ],
        default_provider="anthropic",
        default_model="claude-sonnet-4-20250514"
    )


@router.get("/security-analyzers", response_model=List[str])
async def get_security_analyzers():
    """
    Get available security analyzers.
    """
    return [
        "bandit",
        "safety",
        "semgrep",
        "llm-sec-1"
    ]


# Also add root-level /api routes for compatibility
from fastapi import APIRouter as RootRouter

root_router = RootRouter(tags=["Root Options"])

@root_router.get("/api/options/models", response_model=ModelsResponse)
async def root_get_models():
    return await get_models()

@root_router.get("/api/options/security-analyzers", response_model=List[str])
async def root_get_security_analyzers():
    return await get_security_analyzers()