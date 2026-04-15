"""Mood Schemas"""
from datetime import datetime
from pydantic import BaseModel, Field


EMOJI_OPTIONS = {"wonderful", "good", "okay", "rough", "stressed"}


class MoodLogRequest(BaseModel):
    score: int = Field(..., ge=1, le=10, description="Mood score from 1 (very bad) to 10 (amazing)")
    emoji: str = Field(..., description="Mood label: wonderful/good/okay/rough/stressed")
    note: str | None = Field(None, max_length=500)
    context_tag: str | None = Field(None, max_length=50)

    @classmethod
    def validate_emoji(cls, v: str) -> str:
        if v.lower() not in EMOJI_OPTIONS:
            raise ValueError(f"emoji must be one of {EMOJI_OPTIONS}")
        return v.lower()


class MoodLogOut(BaseModel):
    id: str
    score: int
    emoji: str
    note: str | None
    note_sentiment: float | None
    context_tag: str | None
    logged_at: datetime

    model_config = {"from_attributes": True}


class MoodTrendPoint(BaseModel):
    date: str
    avg_score: float
    dominant_emoji: str
    entry_count: int


class MoodTrendsResponse(BaseModel):
    period: str  # "weekly" | "monthly"
    trend_direction: str  # "improving" | "declining" | "stable"
    trend_data: list[MoodTrendPoint]
    overall_avg: float
    streak_days: int


class MoodHistoryResponse(BaseModel):
    items: list[MoodLogOut]
    total: int
    page: int
    page_size: int
