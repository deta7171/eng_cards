import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name_ru: str


class TopicWithCount(TopicOut):
    word_count: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    name: str | None
    avatar_url: str | None


class WordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    text: str
    translation: str
    transcription: str | None
    part_of_speech: str | None
    examples: list[str]
    cefr_level: str | None
    topic: TopicOut | None


class WordCreate(BaseModel):
    text: str


class FSRSStateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    state: str
    due_date: datetime
    reps: int
    lapses: int


class UserWordOut(BaseModel):
    user_word_id: uuid.UUID
    word: WordOut
    fsrs_state: FSRSStateOut


class WordListOut(BaseModel):
    items: list[WordOut]
    total: int
    page: int


class UserWordListOut(BaseModel):
    items: list[UserWordOut]
    total: int
    page: int


class SuggestionsOut(BaseModel):
    items: list[WordOut]


class ReviewSubmit(BaseModel):
    activity_type: str  # 'flip' | 'multiple_choice' | 'recall'
    # 1-4 (Again/Hard/Good/Easy) for 'flip'; frontend maps correct/incorrect
    # to 3/1 for 'multiple_choice' and 'recall' before sending.
    rating: int


class ReviewResult(BaseModel):
    fsrs_state: FSRSStateOut


class ReviewQueueOut(BaseModel):
    items: list[UserWordOut]


class StatsSummary(BaseModel):
    total_words: int
    due_today: int
    streak_days: int
    mastered: int
    by_topic: list[TopicWithCount]


class StatsHistoryPoint(BaseModel):
    date: str
    reviews: int
    correct: int


class StatsHistory(BaseModel):
    items: list[StatsHistoryPoint]
