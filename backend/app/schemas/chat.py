"""
Chat schemas (Pydantic models).
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class MessageRequest(BaseModel):
    content: str
    conversation_id: Optional[str] = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    user_id: Optional[str] = None
    role: str
    content: str
    created_at: datetime


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int
