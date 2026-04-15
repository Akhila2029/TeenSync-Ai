"""Journal Schemas"""
from datetime import datetime
from pydantic import BaseModel, Field


class JournalCreateRequest(BaseModel):
    title: str | None = Field(None, max_length=255)
    body: str = Field(..., min_length=1, max_length=10_000)
    is_private: bool = True
    linked_mood_score: float | None = Field(None, ge=1, le=10)


class JournalUpdateRequest(BaseModel):
    title: str | None = Field(None, max_length=255)
    body: str | None = Field(None, min_length=1, max_length=10_000)
    is_private: bool | None = None


class NLPAnalysis(BaseModel):
    sentiment_score: float
    sentiment_label: str
    emotion_label: str
    keywords: list[str]
    themes: list[str]
    word_count: int
    readability: str  # "simple" | "moderate" | "complex"


class JournalOut(BaseModel):
    id: str
    title: str | None
    body: str
    sentiment_score: float | None
    sentiment_label: str | None
    emotion_label: str | None
    keywords: list[str] | None
    linked_mood_score: float | None
    is_private: bool
    word_count: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JournalListResponse(BaseModel):
    items: list[JournalOut]
    total: int
    page: int
    page_size: int
