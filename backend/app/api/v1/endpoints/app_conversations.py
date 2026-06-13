"""
App Conversations endpoints for frontend compatibility.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any, Dict

router = APIRouter(prefix="", tags=["App Conversations"])


class AppConversationResponse(BaseModel):
    """Empty app conversation response."""
    id: Optional[str] = None
    status: str = "idle"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class StartTaskResponse(BaseModel):
    """Empty start task response."""
    id: Optional[str] = None
    status: str = "pending"


@router.get("/app-conversations", response_model=List[AppConversationResponse])
async def get_app_conversations():
    """
    Get all app conversations.
    Returns empty list for initial state.
    """
    return []


@router.post("/app-conversations", response_model=AppConversationResponse)
async def create_app_conversation():
    """
    Create a new app conversation.
    Returns empty response for now.
    """
    return AppConversationResponse()


@router.get("/app-conversations/{conversation_id}", response_model=Optional[AppConversationResponse])
async def get_app_conversation(conversation_id: str):
    """
    Get a specific app conversation.
    """
    return None


@router.post("/app-conversations/start-tasks", response_model=Dict[str, Any])
async def start_tasks():
    """
    Start tasks for a conversation.
    Returns empty response.
    """
    return {"id": None, "status": "pending"}


@router.post("/app-conversations/start-tasks/search", response_model=List[StartTaskResponse])
async def start_tasks_search():
    """
    Start tasks with search params.
    Returns empty response.
    """
    return []


@router.get("/app-conversations/batch", response_model=List[AppConversationResponse])
async def batch_get_conversations():
    """
    Batch get conversations.
    Returns empty list.
    """
    return []