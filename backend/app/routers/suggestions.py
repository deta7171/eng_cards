import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import FSRSState, Topic, User, UserWord, Word
from app.schemas import SuggestionsOut, UserWordOut

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


@router.get("", response_model=SuggestionsOut)
def get_suggestions(
    topic: str | None = None,
    level: str | None = None,
    count: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    already_added = select(UserWord.word_id).where(UserWord.user_id == user.id)

    query = select(Word).where(Word.id.not_in(already_added)).where(Word.source == "seed")
    if topic:
        query = query.join(Topic).where(Topic.slug == topic)
    if level:
        query = query.where(Word.cefr_level == level)

    items = db.scalars(query.limit(count)).all()
    return SuggestionsOut(items=items)


@router.post("/{word_id}/add", response_model=UserWordOut, status_code=201)
def add_suggestion(word_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    existing = db.query(UserWord).filter(UserWord.user_id == user.id, UserWord.word_id == word.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Word already in your deck")

    user_word = UserWord(user_id=user.id, word_id=word.id, source="suggested")
    db.add(user_word)
    db.flush()

    fsrs_state = FSRSState(user_word_id=user_word.id)
    db.add(fsrs_state)
    db.commit()
    db.refresh(user_word)

    return UserWordOut(user_word_id=user_word.id, word=user_word.word, fsrs_state=user_word.fsrs_state)
