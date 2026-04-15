"""Mood Tracking Router"""
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
import statistics

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.mood import MoodLog
from app.schemas.mood import (
    MoodLogRequest, MoodLogOut, MoodHistoryResponse,
    MoodTrendsResponse, MoodTrendPoint,
)
from app.services.nlp_service import analyze_sentiment

router = APIRouter(prefix="/mood", tags=["Mood Tracking"])


@router.post("", response_model=MoodLogOut, status_code=201)
async def log_mood(
    body: MoodLogRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Log today's mood with score, emoji, and optional note."""
    note_sentiment = None
    if body.note:
        sentiment = analyze_sentiment(body.note)
        note_sentiment = sentiment["compound"]

    log = MoodLog(
        user_id=current_user.id,
        score=body.score,
        emoji=body.emoji.lower(),
        note=body.note,
        note_sentiment=note_sentiment,
        context_tag=body.context_tag,
    )
    db.add(log)
    await db.flush()
    return MoodLogOut.model_validate(log)


@router.get("/history", response_model=MoodHistoryResponse)
async def get_mood_history(
    days: int = Query(default=30, ge=1, le=365),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve paginated mood log history."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    base_q = (
        select(MoodLog)
        .where(MoodLog.user_id == current_user.id, MoodLog.logged_at >= since)
        .order_by(desc(MoodLog.logged_at))
    )
    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(count_q)).scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(base_q.offset(offset).limit(page_size))
    items = result.scalars().all()
    return MoodHistoryResponse(
        items=[MoodLogOut.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/trends", response_model=MoodTrendsResponse)
async def get_mood_trends(
    period: str = Query(default="weekly", pattern="^(weekly|monthly)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated mood trends with trend direction."""
    days = 7 if period == "weekly" else 30
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(MoodLog)
        .where(MoodLog.user_id == current_user.id, MoodLog.logged_at >= since)
        .order_by(MoodLog.logged_at)
    )
    logs = result.scalars().all()

    # Group by date
    by_date: dict[str, list[MoodLog]] = defaultdict(list)
    for log in logs:
        date_key = log.logged_at.strftime("%Y-%m-%d")
        by_date[date_key].append(log)

    trend_data = []
    all_scores = []
    for date_str, day_logs in sorted(by_date.items()):
        scores = [l.score for l in day_logs]
        avg = statistics.mean(scores)
        all_scores.append(avg)
        emojis = [l.emoji for l in day_logs]
        dominant = max(set(emojis), key=emojis.count)
        trend_data.append(MoodTrendPoint(
            date=date_str,
            avg_score=round(avg, 2),
            dominant_emoji=dominant,
            entry_count=len(day_logs),
        ))

    overall_avg = round(statistics.mean(all_scores), 2) if all_scores else 0.0

    # Trend direction based on first half vs second half average
    if len(all_scores) >= 4:
        mid = len(all_scores) // 2
        first_half_avg = statistics.mean(all_scores[:mid])
        second_half_avg = statistics.mean(all_scores[mid:])
        diff = second_half_avg - first_half_avg
        if diff > 0.5:
            trend_direction = "improving"
        elif diff < -0.5:
            trend_direction = "declining"
        else:
            trend_direction = "stable"
    else:
        trend_direction = "stable"

    # Calculate streak
    streak = await _calculate_streak(current_user.id, db)

    return MoodTrendsResponse(
        period=period,
        trend_direction=trend_direction,
        trend_data=trend_data,
        overall_avg=overall_avg,
        streak_days=streak,
    )


@router.get("/streak")
async def get_streak(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current mood logging streak in days."""
    streak = await _calculate_streak(current_user.id, db)
    return {"user_id": current_user.id, "streak_days": streak}


async def _calculate_streak(user_id: str, db: AsyncSession) -> int:
    """Count consecutive days (from today backwards) with at least one mood log."""
    result = await db.execute(
        select(MoodLog.logged_at)
        .where(MoodLog.user_id == user_id)
        .order_by(desc(MoodLog.logged_at))
    )
    timestamps = result.scalars().all()
    if not timestamps:
        return 0

    dates = sorted({ts.date() for ts in timestamps}, reverse=True)
    today = datetime.now(timezone.utc).date()
    streak = 0
    current = today
    for d in dates:
        if d == current:
            streak += 1
            current -= timedelta(days=1)
        elif d < current:
            break
    return streak
