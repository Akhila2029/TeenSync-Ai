"""Burnout Score ORM Model"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class BurnoutScore(Base):
    __tablename__ = "burnout_scores"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Overall risk score 0-100
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    # "low" | "medium" | "high"
    risk_label: Mapped[str] = mapped_column(String(10), nullable=False)
    # Input features used for scoring
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Number of consecutive negative days used in computation
    consecutive_negative_days: Mapped[int] = mapped_column(Integer, default=0)
    # Average mood score over the analysis window
    avg_mood_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Average journal sentiment over the analysis window
    avg_sentiment: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )

    user = relationship("User", back_populates="burnout_scores")

    def __repr__(self) -> str:
        return f"<BurnoutScore id={self.id!r} risk={self.risk_label!r} score={self.risk_score}>"
