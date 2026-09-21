from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import COOKIE_KWARGS, COOKIE_NAME, create_access_token, get_current_user, oauth
from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_MAX_AGE = settings.jwt_expire_minutes * 60


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
    response = RedirectResponse(url=f"{settings.frontend_url}/dashboard")
    response.set_cookie(COOKIE_NAME, jwt_token, max_age=COOKIE_MAX_AGE, **COOKIE_KWARGS)
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, samesite=COOKIE_KWARGS["samesite"], secure=COOKIE_KWARGS["secure"])
    return {"status": "ok"}
