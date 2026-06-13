"""
Conversations endpoints for frontend compatibility.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Any

router = APIRouter(prefix="", tags=["Conversations"])


class ConversationResponse(BaseModel):
    """Empty conversation response."""
    id: Optional[str] = None
    status: str = "idle"


class PendingMessagesResponse(BaseModel):
    """Empty pending messages response."""
    messages: List[Any] = []


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations():
    """
    Get all conversations.
    Returns empty list for initial state.
    """
    return []


@router.get("/conversations/{conversation_id}", response_model=Optional[ConversationResponse])
async def get_conversation(conversation_id: str):
    """
    Get a specific conversation.
    Returns None for non-existent conversations.
    """
    return None


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation():
    """
    Create a new conversation.
    Returns empty response for now.
    """
    return ConversationResponse()


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation.
    """
    return {"success": True}


@router.get("/conversations/{conversation_id}/pending-messages", response_model=PendingMessagesResponse)
async def get_pending_messages(conversation_id: str):
    """
    Get pending messages for a conversation.
    """
    return PendingMessagesResponse()


@router.get("/conversations/{conversation_id}/microagents")
async def get_microagents(conversation_id: str):
    """
    Get microagents for a conversation.
    """
    return []
