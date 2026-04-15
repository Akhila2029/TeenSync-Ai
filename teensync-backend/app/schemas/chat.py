"""Chatbot Schemas"""
from datetime import datetime
from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None  # Auto-generated if None


class ChatMessageOut(BaseModel):
    id: str
    role: str  # "user" | "assistant"
    content: str
    emotion_detected: str | None
    sentiment_score: str | None
    is_crisis: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceDocOut(BaseModel):
    """Metadata for a RAG-retrieved source document."""
    source: str        # Filename e.g. 'anxiety_coping.txt'
    topic: str         # Human-readable topic label


class ChatResponse(BaseModel):
    session_id: str
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut
    detected_emotion: str
    crisis_detected: bool
    resources: list[str] | None = None         # Crisis helplines if needed
    source_docs: list[SourceDocOut] | None = None  # RAG citations (NEW)
    rag_used: bool = False                     # Whether RAG was used (NEW)
    confidence: str | None = None              # "high" | "medium" | "low" (NEW)


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageOut]
    total: int


class PeerMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)
    display_name: str = Field(..., min_length=1, max_length=30)


class PeerMessageOut(BaseModel):
    id: str
    display_name: str
    content: str
    is_flagged: bool
    sentiment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PeerRoomOut(BaseModel):
    id: str
    name: str
    topic: str | None
    description: str | None
    theme: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
