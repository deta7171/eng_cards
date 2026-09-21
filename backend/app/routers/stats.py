from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import FSRSState, ReviewLog, Topic, User, UserWord, Word
from app.schemas import StatsHistory, StatsHistoryPoint, StatsSummary, TopicWithCount

router = APIRouter(prefix="/stats", tags=["stats"])

MASTERY_STABILITY_THRESHOLD = 21  # days; matches FSRS "long-term memory" rule of thumb


@router.get("/summary", response_model=StatsSummary)
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    base = select(UserWord.id).where(UserWord.user_id == user.id)
    total_words = len(db.scalars(base).all())

    due_today = db.scalar(
        select(func.count())
        .select_from(UserWord)
        .join(FSRSState)
        .where(UserWord.user_id == user.id)
        .where(FSRSState.due_date <= datetime.now(timezone.utc))
    ) or 0

    mastered = db.scalar(
        select(func.count())
        .select_from(UserWord)
        .join(FSRSState)
        .where(UserWord.user_id == user.id)
        .where(FSRSState.stability >= MASTERY_STABILITY_THRESHOLD)
    ) or 0

    by_topic_rows = db.execute(
        select(Topic.slug, Topic.name_ru, func.count(UserWord.id))
        .select_from(UserWord)
        .join(Word, Word.id == UserWord.word_id)
        .join(Topic, Topic.id == Word.topic_id)
        .where(UserWord.user_id == user.id)
        .group_by(Topic.id)
    ).all()

    streak_days = _compute_streak(db, user.id)

    return StatsSummary(
        total_words=total_words,
        due_today=due_today,
        streak_days=streak_days,
        mastered=mastered,
        by_topic=[TopicWithCount(slug=slug, name_ru=name_ru, word_count=count) for slug, name_ru, count in by_topic_rows],
    )


def _compute_streak(db: Session, user_id) -> int:
    rows = db.execute(
        select(func.date(ReviewLog.reviewed_at))
        .select_from(ReviewLog)
        .join(UserWord, UserWord.id == ReviewLog.user_word_id)
        .where(UserWord.user_id == user_id)
        .distinct()
        .order_by(func.date(ReviewLog.reviewed_at).desc())
    ).all()
    review_dates = {row[0] for row in rows}

    streak = 0
    day = datetime.now(timezone.utc).date()
    while day in review_dates:
        streak += 1
        day -= timedelta(days=1)
    return streak


@router.get("/history", response_model=StatsHistory)
def history(days: int = Query(30, ge=1, le=365), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(
            func.date(ReviewLog.reviewed_at),
            func.count(),
            func.sum(func.cast(ReviewLog.rating >= 3, Integer)),
        )
        .select_from(ReviewLog)
        .join(UserWord, UserWord.id == ReviewLog.user_word_id)
        .where(UserWord.user_id == user.id)
        .where(ReviewLog.reviewed_at >= since)
        .group_by(func.date(ReviewLog.reviewed_at))
        .order_by(func.date(ReviewLog.reviewed_at))
    ).all()

    return StatsHistory(
        items=[
            StatsHistoryPoint(date=str(date), reviews=reviews, correct=correct or 0)
            for date, reviews, correct in rows
        ]
    )
