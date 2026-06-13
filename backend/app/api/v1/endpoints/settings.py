"""
Settings endpoints for frontend compatibility.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingsResponse(BaseModel):
    """Default settings for ManusAI OSS mode."""
    llm_model: str = "claude-sonnet-4-20250514"
    llm_base_url: Optional[str] = None
    agent: str = "default"
    llm_api_key: Optional[str] = None
    llm_api_key_set: bool = False
    confirmation_mode: bool = False
    security_analyzer: str = "bandit"
    max_iterations: int = 100
    enable_default_condenser: bool = True
    condenser_max_size: int = 4000
    mcp_config: Optional[Dict[str, Any]] = None
    search_api_key: Optional[str] = None
    email: Optional[str] = None
    git_user_name: str = ""
    git_user_email: str = ""
    is_new_user: bool = True
    disabled_skills: List[str] = []
    v1_enabled: bool = True
    agent_settings: Dict[str, Any] = {}
    agent_settings_schema: Optional[Dict[str, Any]] = None
    conversation_settings: Dict[str, Any] = {}
    conversation_settings_schema: Optional[Dict[str, Any]] = None
    sandbox_grouping_strategy: str = "by-conversation"
    app_mode: str = "oss"


class SettingsSchemaResponse(BaseModel):
    """Empty schema for OSS mode."""
    type: str = "object"
    properties: Dict[str, Any] = {}


@router.get("", response_model=SettingsResponse)
async def get_settings():
    """
    Get current user settings.
    For OSS mode, returns default settings.
    """
    return SettingsResponse()


@router.get("/agent-schema", response_model=SettingsSchemaResponse)
async def get_agent_schema():
    """
    Get agent settings schema.
    Returns empty schema for OSS mode.
    """
    return SettingsSchemaResponse()


@router.get("/conversation-schema", response_model=SettingsSchemaResponse)
async def get_conversation_schema():
    """
    Get conversation settings schema.
    Returns empty schema for OSS mode.
    """
    return SettingsSchemaResponse()


@router.post("")
async def save_settings():
    """
    Save settings.
    No-op for OSS mode.
    """
    return {"success": True}