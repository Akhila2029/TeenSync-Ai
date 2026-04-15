"""Journal Router – CRUD + NLP analysis"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.journal import JournalEntry
from app.schemas.journal import (
    JournalCreateRequest, JournalUpdateRequest,
    JournalOut, JournalListResponse, NLPAnalysis,
)
from app.services.nlp_service import full_nlp_analysis

router = APIRouter(prefix="/journal", tags=["Journal"])


@router.post("", response_model=JournalOut, status_code=201)
async def create_entry(
    body: JournalCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new journal entry with automatic NLP analysis."""
    nlp = full_nlp_analysis(body.body)
    entry = JournalEntry(
        user_id=current_user.id,
        title=body.title,
        body=body.body,
        is_private=body.is_private,
        linked_mood_score=body.linked_mood_score,
        sentiment_score=nlp["sentiment_score"],
        sentiment_label=nlp["sentiment_label"],
        emotion_label=nlp["emotion_label"],
        keywords=nlp["keywords"],
        word_count=nlp["word_count"],
    )
    db.add(entry)
    await db.flush()
    return JournalOut.model_validate(entry)


@router.get("", response_model=JournalListResponse)
async def list_entries(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all non-deleted journal entries (paginated)."""
    base_q = (
        select(JournalEntry)
        .where(JournalEntry.user_id == current_user.id, JournalEntry.is_deleted == False)
        .order_by(desc(JournalEntry.created_at))
    )
    total = (await db.execute(select(func.count()).select_from(base_q.subquery()))).scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(base_q.offset(offset).limit(page_size))
    items = result.scalars().all()
    return JournalListResponse(
        items=[JournalOut.model_validate(e) for e in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{entry_id}", response_model=JournalOut)
async def get_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single journal entry by ID."""
    entry = await _get_owned_entry(entry_id, current_user.id, db)
    return JournalOut.model_validate(entry)


@router.put("/{entry_id}", response_model=JournalOut)
async def update_entry(
    entry_id: str,
    body: JournalUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a journal entry, re-running NLP on new body if provided."""
    entry = await _get_owned_entry(entry_id, current_user.id, db)

    if body.title is not None:
        entry.title = body.title
    if body.is_private is not None:
        entry.is_private = body.is_private
    if body.body is not None:
        nlp = full_nlp_analysis(body.body)
        entry.body = body.body
        entry.sentiment_score = nlp["sentiment_score"]
        entry.sentiment_label = nlp["sentiment_label"]
        entry.emotion_label = nlp["emotion_label"]
        entry.keywords = nlp["keywords"]
        entry.word_count = nlp["word_count"]

    return JournalOut.model_validate(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a journal entry."""
    entry = await _get_owned_entry(entry_id, current_user.id, db)
    entry.is_deleted = True


@router.get("/{entry_id}/analysis", response_model=NLPAnalysis)
async def get_entry_analysis(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-run and return the full NLP analysis for a journal entry."""
    entry = await _get_owned_entry(entry_id, current_user.id, db)
    nlp = full_nlp_analysis(entry.body)
    return NLPAnalysis(
        sentiment_score=nlp["sentiment_score"],
        sentiment_label=nlp["sentiment_label"],
        emotion_label=nlp["emotion_label"],
        keywords=nlp["keywords"],
        themes=nlp["themes"],
        word_count=nlp["word_count"],
        readability=nlp["readability"],
    )


async def _get_owned_entry(entry_id: str, user_id: str, db: AsyncSession) -> JournalEntry:
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.user_id == user_id,
            JournalEntry.is_deleted == False,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    return entry
