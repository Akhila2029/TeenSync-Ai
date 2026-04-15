"""
TeenSync – Chat Router
Handles Luna AI chatbot interactions using the RAG-augmented chatbot service.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.chat import ChatMessage
from app.models.user import User
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageOut,
    ChatResponse,
    ChatHistoryResponse,
    SourceDocOut,
)
from app.services.chatbot_service import generate_response
from app.services.rag_service import get_rag_status

router = APIRouter(prefix="/chat", tags=["Chatbot"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.post("/message", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def send_message(
    body: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message to Luna (AI chatbot) and receive a RAG-augmented empathetic response.

    Flow:
      1. Load or create conversation session
      2. Retrieve last 6 messages as conversation history
      3. Run RAG-augmented chatbot pipeline (emotion + retrieval + LLM)
      4. Persist both user message and assistant reply to DB
      5. Return full response with source citations
    """
    # ── Session management ────────────────────────────────────────────────────
    session_id = body.session_id or str(uuid.uuid4())

    # ── Fetch recent conversation history ────────────────────────────────────
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id, ChatMessage.session_id == session_id)
        .order_by(desc(ChatMessage.created_at))
        .limit(6)  # last 3 turns (user + assistant each)
    )
    recent_msgs = list(reversed(history_result.scalars().all()))
    conversation_history = [
        {"role": m.role, "content": m.content}
        for m in recent_msgs
    ]

    # ── Generate response via RAG pipeline ────────────────────────────────────
    result = await generate_response(
        user_text=body.message,
        conversation_history=conversation_history,
    )

    now = _utcnow()

    # ── Persist user message ──────────────────────────────────────────────────
    user_msg = ChatMessage(
        user_id=current_user.id,
        session_id=session_id,
        role="user",
        content=body.message,
        emotion_detected=result["emotion_detected"],
        sentiment_score=str(round(result["sentiment_score"], 4)),
        is_crisis=result["is_crisis"],
        created_at=now,
    )
    db.add(user_msg)
    await db.flush()

    # ── Persist assistant message ─────────────────────────────────────────────
    assistant_msg = ChatMessage(
        user_id=current_user.id,
        session_id=session_id,
        role="assistant",
        content=result["response"],
        emotion_detected=result["emotion_detected"],
        sentiment_score=None,
        is_crisis=False,
        created_at=now,
    )
    db.add(assistant_msg)
    await db.flush()

    # ── Build source doc list ─────────────────────────────────────────────────
    source_docs: Optional[list[SourceDocOut]] = None
    if result.get("source_docs"):
        source_docs = [
            SourceDocOut(
                source=d.get("source", ""),
                topic=d.get("topic", ""),
            )
            for d in result["source_docs"]
        ]

    # ── Return response ───────────────────────────────────────────────────────
    return ChatResponse(
        session_id=session_id,
        user_message=ChatMessageOut.model_validate(user_msg),
        assistant_message=ChatMessageOut.model_validate(assistant_msg),
        detected_emotion=result["emotion_detected"],
        crisis_detected=result["is_crisis"],
        resources=result.get("resources"),
        source_docs=source_docs,
        rag_used=result.get("rag_used", False),
        confidence=result.get("confidence"),
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str = Query(..., description="Chat session ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve paginated chat history for a session."""
    from sqlalchemy import func

    base_q = (
        select(ChatMessage)
        .where(
            ChatMessage.user_id == current_user.id,
            ChatMessage.session_id == session_id,
        )
        .order_by(ChatMessage.created_at)
    )
    total = (
        await db.execute(select(func.count()).select_from(base_q.subquery()))
    ).scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(base_q.offset(offset).limit(page_size))
    messages = result.scalars().all()

    return ChatHistoryResponse(
        session_id=session_id,
        messages=[ChatMessageOut.model_validate(m) for m in messages],
        total=total,
    )


@router.get("/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a list of distinct chat session IDs for the current user."""
    from sqlalchemy import distinct

    result = await db.execute(
        select(distinct(ChatMessage.session_id))
        .where(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.session_id)
    )
    session_ids = result.scalars().all()
    return {"user_id": current_user.id, "sessions": session_ids, "total": len(session_ids)}


@router.get("/rag/status")
async def rag_status(current_user: User = Depends(get_current_user)):
    """Return RAG system status — useful for debugging and health checks."""
    return get_rag_status()
