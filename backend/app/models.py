import uuid
from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_id: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str | None]
    avatar_url: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    words: Mapped[list["UserWord"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(unique=True)
    name_en: Mapped[str]
    name_ru: Mapped[str]


class Word(Base):
    __tablename__ = "words"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text: Mapped[str] = mapped_column(unique=True, index=True)
    translation: Mapped[str]
    transcription: Mapped[str | None]
    part_of_speech: Mapped[str | None]
    examples: Mapped[list] = mapped_column(JSONB, default=list)
    audio_url: Mapped[str | None]
    cefr_level: Mapped[str | None]
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id"))
    source: Mapped[str] = mapped_column(default="user_added")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    topic: Mapped[Topic | None] = relationship()


class UserWord(Base):
    __tablename__ = "user_words"
    __table_args__ = (UniqueConstraint("user_id", "word_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    word_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(default="manual")
    added_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped[User] = relationship(back_populates="words")
    word: Mapped[Word] = relationship()
    fsrs_state: Mapped["FSRSState"] = relationship(back_populates="user_word", uselist=False, cascade="all, delete-orphan")


class FSRSState(Base):
    __tablename__ = "fsrs_states"

    user_word_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_words.id", ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[str] = mapped_column(default="new")
    step: Mapped[int | None]
    stability: Mapped[float | None]
    difficulty: Mapped[float | None]
    due_date: Mapped[datetime] = mapped_column(server_default=func.now())
    reps: Mapped[int] = mapped_column(default=0)
    lapses: Mapped[int] = mapped_column(default=0)
    last_review: Mapped[datetime | None]

    user_word: Mapped[UserWord] = relationship(back_populates="fsrs_state")


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_word_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_words.id", ondelete="CASCADE"))
    activity_type: Mapped[str]
    rating: Mapped[int]
    elapsed_days: Mapped[float | None]
    reviewed_at: Mapped[datetime] = mapped_column(server_default=func.now())
