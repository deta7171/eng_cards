import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import engine
from app.routers import auth, review, stats, suggestions, topics, words

logger = logging.getLogger("app.timing")

app = FastAPI(title="eng_cards API")


@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info("%s %s %.1fms", request.method, request.url.path, elapsed_ms)
    response.headers["Server-Timing"] = f"total;dur={elapsed_ms:.1f}"
    return response

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


@app.get("/api/health/db")
def health_db():
    """Diagnostic: isolates the raw DB round-trip (one SELECT 1) from
    everything else, to tell network/Render-container overhead apart from
    actual Neon query latency."""
    start = time.perf_counter()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    elapsed_ms = (time.perf_counter() - start) * 1000
    return {"status": "ok", "db_query_ms": round(elapsed_ms, 1)}
