"""Chat Message ORM Model"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Groups messages into a conversation session
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # "user" | "assistant"
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Emotion detected in this message (for user messages)
    emotion_detected: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # VADER sentiment score of this message
    sentiment_score: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Whether crisis keywords were detected
    is_crisis: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )

    user = relationship("User", back_populates="chat_messages")

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id!r} role={self.role!r}>"
