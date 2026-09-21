from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.routers import auth, review, stats, suggestions, topics, words

app = FastAPI(title="eng_cards API")

# required by Authlib's Starlette integration to stash the OAuth `state`
# between /auth/google/login and /auth/google/callback. Only used transiently
# during that same-site redirect dance - app auth itself is a bearer token
# (see app.auth.get_current_user), not a cookie.
app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret, session_cookie="oauth_state")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(words.router, prefix="/api")
app.include_router(suggestions.router, prefix="/api")
app.include_router(topics.router, prefix="/api")
app.include_router(review.router, prefix="/api")
app.include_router(stats.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
