"""Mood Tracking ORM Model"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class MoodLog(Base):
    __tablename__ = "mood_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Mood score 1-10 (1=very bad, 10=amazing)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    # Emoji identifier: "wonderful", "good", "okay", "rough", "stressed"
    emoji: Mapped[str] = mapped_column(String(50), nullable=False)
    # Optional free-text note about the mood
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Sentiment of the note (if provided), computed by NLP
    note_sentiment: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Context tags e.g. "school", "family", "health"
    context_tag: Mapped[str | None] = mapped_column(String(50), nullable=True)
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )

    user = relationship("User", back_populates="mood_logs")

    def __repr__(self) -> str:
        return f"<MoodLog id={self.id!r} score={self.score} emoji={self.emoji!r}>"
