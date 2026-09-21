from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Topic, Word
from app.schemas import TopicWithCount

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("", response_model=list[TopicWithCount])
def list_topics(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Topic.slug, Topic.name_ru, func.count(Word.id))
        .join(Word, Word.topic_id == Topic.id, isouter=True)
        .group_by(Topic.id)
    ).all()
    return [TopicWithCount(slug=slug, name_ru=name_ru, word_count=count) for slug, name_ru, count in rows]
