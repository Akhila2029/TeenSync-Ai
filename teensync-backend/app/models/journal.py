"""Journal Entry ORM Model"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # ── NLP Analysis Fields ──────────────────────────────────────────────────────
    # VADER compound score: -1.0 (negative) to +1.0 (positive)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Sentiment label: "positive", "neutral", "negative"
    sentiment_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Detected emotion: "happy", "sad", "anxious", "angry", "hopeful", "stressed", "neutral"
    emotion_label: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # JSON list of extracted keywords/themes
    keywords: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Mood score linked at time of writing (optional)
    linked_mood_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Metadata ─────────────────────────────────────────────────────────────────
    is_private: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    word_count: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    user = relationship("User", back_populates="journal_entries")

    def __repr__(self) -> str:
        return f"<JournalEntry id={self.id!r} sentiment={self.sentiment_label!r}>"
