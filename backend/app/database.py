from datetime import datetime

from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    # Every datetime column is timestamptz (see alembic/versions/0001_initial.py).
    # Without this, a bare `Mapped[datetime]` infers a timezone-naive column,
    # which drifts from the actual migrated schema and produces naive
    # datetimes that can't be compared against the aware ones fsrs expects.
    type_annotation_map = {datetime: DateTime(timezone=True)}


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
