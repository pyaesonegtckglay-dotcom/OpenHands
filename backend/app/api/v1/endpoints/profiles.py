"""
Profiles endpoints for frontend compatibility.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="", tags=["Profiles"])


class LlmProfile(BaseModel):
    name: str
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key_set: bool = False


class LlmProfileListResponse(BaseModel):
    profiles: List[LlmProfile] = []
    active_profile: Optional[str] = None


@router.get("/settings/profiles", response_model=LlmProfileListResponse)
async def list_profiles():
    """
    List LLM profiles.
    Returns empty list for OSS mode.
    """
    return LlmProfileListResponse(profiles=[], active_profile=None)


@router.post("/settings/profiles/{name}")
async def save_profile(name: str):
    """
    Save a profile.
    No-op for OSS mode.
    """
    return {"success": True}


@router.delete("/settings/profiles/{name}")
async def delete_profile(name: str):
    """
    Delete a profile.
    No-op for OSS mode.
    """
    return {"success": True}


@router.post("/settings/profiles/{name}/activate")
async def activate_profile(name: str):
    """
    Activate a profile.
    No-op for OSS mode.
    """
    return {"success": True}


@router.post("/settings/profiles/{name}/rename")
async def rename_profile(name: str):
    """
    Rename a profile.
    No-op for OSS mode.
    """
    return {"success": True}