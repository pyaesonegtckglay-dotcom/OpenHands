"""
Conversations endpoints for frontend compatibility.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional, Any, Dict

router = APIRouter(prefix="/conversations", tags=["Conversations"])


class ConversationResponse(BaseModel):
    """Empty conversation response."""
    id: Optional[str] = None
    status: str = "idle"


class PendingMessagesResponse(BaseModel):
    """Empty pending messages response."""
    messages: List[Any] = []


@router.get("", response_model=List[ConversationResponse])
async def get_conversations():
    """
    Get all conversations.
    Returns empty list for initial state.
    """
    return []


@router.get("/{conversation_id}", response_model=Optional[ConversationResponse])
async def get_conversation(conversation_id: str):
    """
    Get a specific conversation.
    Returns None for non-existent conversations.
    """
    return None


@router.post("", response_model=ConversationResponse)
async def create_conversation():
    """
    Create a new conversation.
    Returns empty response for now.
    """
    return ConversationResponse()


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation.
    """
    return {"success": True}


@router.get("/{conversation_id}/pending-messages", response_model=PendingMessagesResponse)
async def get_pending_messages(conversation_id: str):
    """
    Get pending messages for a conversation.
    """
    return PendingMessagesResponse()


@router.get("/{conversation_id}/microagents")
async def get_microagents(conversation_id: str):
    """
    Get microagents for a conversation.
    """
    return []


# Also add root-level /api routes for compatibility
from fastapi import APIRouter as RootRouter

root_router = RootRouter(tags=["Root Conversations"])

@root_router.get("/api/conversations", response_model=List[ConversationResponse])
async def root_get_conversations():
    return await get_conversations()

@root_router.get("/api/conversations/{conversation_id}", response_model=Optional[ConversationResponse])
async def root_get_conversation(conversation_id: str):
    return await get_conversation(conversation_id)

@root_router.post("/api/conversations", response_model=ConversationResponse)
async def root_create_conversation():
    return await create_conversation()

@root_router.delete("/api/conversations/{conversation_id}")
async def root_delete_conversation(conversation_id: str):
    return await delete_conversation(conversation_id)