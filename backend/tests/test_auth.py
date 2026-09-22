import uuid

import jwt
import pytest

from app.auth import create_access_token


def test_me_without_token_is_401(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_garbage_token_is_401(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert resp.status_code == 401


def test_me_with_non_bearer_scheme_is_401(client, make_user):
    user = make_user()
    token = create_access_token(user.id)
    resp = client.get("/api/auth/me", headers={"Authorization": f"Token {token}"})
    assert resp.status_code == 401


def test_me_with_expired_token_is_401(client, make_user):
    from datetime import datetime, timedelta, timezone

    user = make_user()
    expired_payload = {"sub": str(user.id), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}
    expired_token = jwt.encode(expired_payload, "test-secret-for-pytest-only", algorithm="HS256")
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401


def test_me_for_deleted_user_is_401(client, make_user, db_session):
    user = make_user()
    token = create_access_token(user.id)
    db_session.delete(user)
    db_session.commit()

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_me_for_random_uuid_not_in_db_is_401(client):
    token = create_access_token(uuid.uuid4())
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_me_returns_correct_user(client, make_user):
    user = make_user(email="me@example.com", name="Alice")
    token = create_access_token(user.id)

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me@example.com"
    assert body["name"] == "Alice"
    assert body["id"] == str(user.id)


def test_google_login_redirects_to_google_with_correct_params(client):
    resp = client.get("/api/auth/google/login", follow_redirects=False)
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "client_id=test-client-id" in location
    assert "state=" in location


def test_google_callback_creates_user_and_redirects_with_token(client, monkeypatch, db_session):
    from app import routers

    async def fake_authorize_access_token(request):
        return {
            "userinfo": {
                "sub": "google-sub-123",
                "email": "newuser@example.com",
                "name": "New User",
                "picture": "https://example.com/avatar.png",
            }
        }

    monkeypatch.setattr(routers.auth.oauth.google, "authorize_access_token", fake_authorize_access_token)

    resp = client.get("/api/auth/google/callback", follow_redirects=False)
    assert resp.status_code == 307 or resp.status_code == 302

    location = resp.headers["location"]
    assert location.startswith("http://localhost:5173/auth/callback?token=")

    from app.models import User

    user = db_session.query(User).filter(User.google_id == "google-sub-123").first()
    assert user is not None
    assert user.email == "newuser@example.com"
    assert user.name == "New User"


def test_google_callback_reuses_existing_user(client, monkeypatch, make_user, db_session):
    from app import routers

    existing = make_user(email="existing@example.com", google_id="existing-sub")

    async def fake_authorize_access_token(request):
        return {"userinfo": {"sub": "existing-sub", "email": "existing@example.com", "name": "Existing"}}

    monkeypatch.setattr(routers.auth.oauth.google, "authorize_access_token", fake_authorize_access_token)

    client.get("/api/auth/google/callback", follow_redirects=False)

    from app.models import User

    count = db_session.query(User).filter(User.google_id == "existing-sub").count()
    assert count == 1
