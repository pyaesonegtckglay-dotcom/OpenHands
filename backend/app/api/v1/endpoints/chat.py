"""
Chat endpoints - Phase 0 minimal communication layer.
"""
from asyncpg import Connection
from fastapi import APIRouter, Depends
from typing import List

from app.database.connection import get_db
from app.core.security import get_current_user
from app.schemas.chat import (
    MessageRequest, MessageResponse,
    ConversationListResponse,
)
from app.services.chat_service import (
    send_message, get_conversation_messages, list_conversations
)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/message", response_model=List[MessageResponse])
async def post_message(
    data: MessageRequest,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Send a message and receive response. Phase 0: minimal echo."""
    return await send_message(conn, current_user["user_id"], data)


@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all conversations for the current user."""
    convs = await list_conversations(conn, current_user["user_id"])
    return ConversationListResponse(conversations=convs, total=len(convs))


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get all messages in a conversation."""
    return await get_conversation_messages(conn, current_user["user_id"], conversation_id)
