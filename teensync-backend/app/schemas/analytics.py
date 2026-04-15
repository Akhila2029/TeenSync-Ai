"""Analytics and Dashboard Schemas"""
from pydantic import BaseModel


class MoodDayPoint(BaseModel):
    day: str
    score: float
    emoji: str


class EmotionSlice(BaseModel):
    emotion: str
    count: int
    percentage: float


class EngagementStats(BaseModel):
    sessions_this_week: int
    journal_entries_this_week: int
    mood_logs_this_week: int
    avg_session_length_min: float
    streak_days: int


class BurnoutSummary(BaseModel):
    risk_score: float
    risk_label: str
    consecutive_negative_days: int
    recommendation: str


class DashboardResponse(BaseModel):
    user_id: str
    username: str
    weekly_mood_trend: list[MoodDayPoint]
    overall_mood_avg: float
    emotion_distribution: list[EmotionSlice]
    engagement: EngagementStats
    burnout: BurnoutSummary
    total_journal_entries: int
    total_mood_logs: int


class RecommendationItem(BaseModel):
    type: str  # "breathing" | "journal_prompt" | "tip" | "resource" | "session"
    title: str
    description: str
    action_label: str
    priority: int  # 1 = highest


class RecommendationsResponse(BaseModel):
    user_id: str
    based_on: dict  # Summary of inputs used
    items: list[RecommendationItem]


class BurnoutRiskResponse(BaseModel):
    user_id: str
    risk_score: float
    risk_label: str
    analysis: dict
    needs_professional_help: bool
    recommendations: list[str]


class ParentInsightsResponse(BaseModel):
    child_user_id: str
    weekly_mood_avg: float
    mood_trend: str
    engagement_level: str  # "high" | "medium" | "low"
    streak_days: int
    last_active: str | None
    general_wellness: str


class CounselorAggregateResponse(BaseModel):
    total_users: int
    avg_mood_score: float
    emotion_distribution: list[EmotionSlice]
    burnout_risk_distribution: dict
    engagement_by_day: list[dict]
    stress_heatmap: list[dict]
    period_days: int
