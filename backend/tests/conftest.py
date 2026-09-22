import os

os.environ["DATABASE_URL"] = "postgresql://eng_cards:eng_cards@localhost:5433/eng_cards_test"
os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
os.environ["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
os.environ["JWT_SECRET"] = "test-secret-for-pytest-only"
os.environ["FRONTEND_URL"] = "http://localhost:5173"

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models import FSRSState, Topic, User, UserWord, Word
from app.services import dictionary, translation

engine = create_engine(os.environ["DATABASE_URL"])
TestingSessionLocal = sessionmaker(bind=engine)

BACKEND_ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    # Run the real Alembic migrations rather than Base.metadata.create_all():
    # tests must validate against the schema that actually gets deployed
    # (create_all() previously diverged on timezone-naive vs aware datetime
    # columns and masked a real bug).
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.upgrade(cfg, "head")
    yield
    command.downgrade(cfg, "base")


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture(autouse=True)
def _mock_external_services(monkeypatch):
    """Every test is isolated from MyMemory/Free Dictionary by default -
    both real APIs are rate-limited/flaky, and tests must not depend on
    network access. Individual tests can monkeypatch further to exercise
    failure paths (see test_words.py)."""

    async def fake_translate(text: str) -> str:
        return f"перевод-{text}"

    async def fake_lookup(word: str):
        return None

    monkeypatch.setattr(translation, "translate_en_to_ru", fake_translate)
    monkeypatch.setattr(dictionary, "lookup", fake_lookup)


@pytest.fixture()
def db_session():
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db_session):
    def _make(email="user@example.com", google_id="google-id-1", name="Test User"):
        user = User(google_id=google_id, email=email, name=name)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


def auth_headers(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture()
def auth_client(client, make_user):
    """A TestClient with a default Authorization header for its own user.

    `client` and `auth_client` are the SAME underlying object (fixture
    values are cached per test), so a second test user must NOT be logged
    in by mutating client.headers - that clobbers auth_client's header too.
    Pass `headers=auth_headers(other_user)` on that specific request instead.
    """
    user = make_user()
    client.headers.update(auth_headers(user))
    client.current_user = user
    return client


@pytest.fixture()
def make_topic(db_session):
    def _make(slug="food", name_en="Food", name_ru="Еда"):
        topic = Topic(slug=slug, name_en=name_en, name_ru=name_ru)
        db_session.add(topic)
        db_session.commit()
        db_session.refresh(topic)
        return topic

    return _make


@pytest.fixture()
def make_word(db_session):
    def _make(text="apple", translation_="яблоко", topic=None, cefr_level=None, source="seed"):
        word = Word(
            text=text,
            translation=translation_,
            topic_id=topic.id if topic else None,
            cefr_level=cefr_level,
            source=source,
        )
        db_session.add(word)
        db_session.commit()
        db_session.refresh(word)
        return word

    return _make


@pytest.fixture()
def make_user_word(db_session):
    def _make(user, word, source="manual"):
        user_word = UserWord(user_id=user.id, word_id=word.id, source=source)
        db_session.add(user_word)
        db_session.flush()
        fsrs_state = FSRSState(user_word_id=user_word.id)
        db_session.add(fsrs_state)
        db_session.commit()
        db_session.refresh(user_word)
        return user_word

    return _make
