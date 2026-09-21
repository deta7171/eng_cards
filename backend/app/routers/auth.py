from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, oauth
from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google/login")
async def google_login(request: Request):
    return await oauth.google.authorize_redirect(request, settings.google_redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token["userinfo"]

    user = db.query(User).filter(User.google_id == userinfo["sub"]).first()
    if user is None:
        user = User(
            google_id=userinfo["sub"],
            email=userinfo["email"],
            name=userinfo.get("name"),
            avatar_url=userinfo.get("picture"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    jwt_token = create_access_token(user.id)
    # Hand the token to the frontend via a redirect query param rather than a
    # cookie: frontend and backend are on different sites in production, and
    # cross-site cookies are unreliable (see app.auth.get_current_user). The
    # frontend reads this once on /auth/callback and stores it itself.
    query = urlencode({"token": jwt_token})
    return RedirectResponse(url=f"{settings.frontend_url}/auth/callback?{query}")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
