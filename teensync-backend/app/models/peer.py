"""Peer Support ORM Models"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class PeerRoom(Base):
    __tablename__ = "peer_rooms"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    topic: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_members: Mapped[int] = mapped_column(Integer, default=50)
    # Emoji or color theme identifier
    theme: Mapped[str] = mapped_column(String(20), default="calm")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    messages = relationship("PeerMessage", back_populates="room", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<PeerRoom id={self.id!r} name={self.name!r}>"


class PeerMessage(Base):
    __tablename__ = "peer_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    room_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("peer_rooms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Stored as anonymized display name, not real user_id
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Flagged by moderation
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Sentiment score of message
    sentiment: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )

    room = relationship("PeerRoom", back_populates="messages")

    def __repr__(self) -> str:
        return f"<PeerMessage id={self.id!r} room={self.room_id!r}>"
