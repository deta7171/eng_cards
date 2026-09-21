import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import FSRSState, Topic, User, UserWord, Word
from app.schemas import UserWordListOut, UserWordOut, WordCreate, WordListOut
from app.services import dictionary, translation

router = APIRouter(tags=["words"])

PAGE_SIZE = 20


@router.get("/user-words", response_model=UserWordListOut)
def list_user_words(
    page: int = Query(1, ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(UserWord).where(UserWord.user_id == user.id).order_by(UserWord.added_at.desc())
    total = len(db.scalars(query).all())
    items = db.scalars(query.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)).all()
    return UserWordListOut(
        items=[UserWordOut(user_word_id=uw.id, word=uw.word, fsrs_state=uw.fsrs_state) for uw in items],
        total=total,
        page=page,
    )


@router.get("/words", response_model=WordListOut)
def list_words(
    topic: str | None = None,
    level: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    query = select(Word)
    if topic:
        query = query.join(Topic).where(Topic.slug == topic)
    if level:
        query = query.where(Word.cefr_level == level)
    if search:
        query = query.where(Word.text.ilike(f"%{search}%"))

    total = len(db.scalars(query).all())
    items = db.scalars(query.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)).all()
    return WordListOut(items=items, total=total, page=page)


async def _get_or_create_word(db: Session, text: str) -> Word:
    normalized = text.strip().lower()
    word = db.query(Word).filter(Word.text == normalized).first()
    if word:
        return word

    try:
        translated = await translation.translate_en_to_ru(normalized)
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Translation service unavailable, try again") from exc

    lookup = await dictionary.lookup(normalized)

    word = Word(
        text=normalized,
        translation=translated,
        transcription=lookup.transcription if lookup else None,
        part_of_speech=lookup.part_of_speech if lookup else None,
        examples=lookup.examples if lookup else [],
        audio_url=lookup.audio_url if lookup else None,
        source="user_added",
    )
    db.add(word)
    db.flush()
    return word


@router.post("/words", response_model=UserWordOut, status_code=201)
async def add_word(
    payload: WordCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    word = await _get_or_create_word(db, payload.text)

    existing = db.query(UserWord).filter(UserWord.user_id == user.id, UserWord.word_id == word.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Word already in your deck")

    user_word = UserWord(user_id=user.id, word_id=word.id, source="manual")
    db.add(user_word)
    db.flush()

    fsrs_state = FSRSState(user_word_id=user_word.id)
    db.add(fsrs_state)
    db.commit()
    db.refresh(user_word)

    return UserWordOut(user_word_id=user_word.id, word=user_word.word, fsrs_state=user_word.fsrs_state)


@router.delete("/user-words/{user_word_id}", status_code=204)
def remove_word(user_word_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_word = db.query(UserWord).filter(UserWord.id == user_word_id, UserWord.user_id == user.id).first()
    if not user_word:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(user_word)
    db.commit()
