import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import FSRSState, ReviewLog, User, UserWord
from app.schemas import ReviewQueueOut, ReviewResult, ReviewSubmit, UserWordOut
from app.services import fsrs_service

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue", response_model=ReviewQueueOut)
def get_queue(limit: int = Query(20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = (
        select(UserWord)
        .join(FSRSState)
        .where(UserWord.user_id == user.id)
        .where(FSRSState.due_date <= datetime.now(timezone.utc))
        .order_by(FSRSState.due_date)
        .limit(limit)
    )
    items = db.scalars(query).all()
    return ReviewQueueOut(
        items=[UserWordOut(user_word_id=uw.id, word=uw.word, fsrs_state=uw.fsrs_state) for uw in items]
    )


@router.post("/{user_word_id}", response_model=ReviewResult)
def submit_review(
    user_word_id: uuid.UUID,
    payload: ReviewSubmit,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.rating not in (1, 2, 3, 4):
        raise HTTPException(status_code=422, detail="rating must be 1-4")

    user_word = db.query(UserWord).filter(UserWord.id == user_word_id, UserWord.user_id == user.id).first()
    if not user_word:
        raise HTTPException(status_code=404, detail="Not found")

    fsrs_state = user_word.fsrs_state
    previous_review = fsrs_state.last_review
    fsrs_service.review(fsrs_state, payload.rating)

    elapsed_days = None
    if previous_review:
        elapsed_days = (fsrs_state.last_review - previous_review).total_seconds() / 86400

    db.add(
        ReviewLog(
            user_word_id=user_word.id,
            activity_type=payload.activity_type,
            rating=payload.rating,
            elapsed_days=elapsed_days,
        )
    )
    db.commit()
    db.refresh(fsrs_state)

    return ReviewResult(fsrs_state=fsrs_state)
