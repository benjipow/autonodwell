"""Authentication & authorization.

Every visitor gets a Firebase user (anonymous at first). When they sign in with
email/Google, the web app *links* the anonymous account, so the Firebase UID — and
therefore every design they made — stays the same. Roles live in our database,
not in Firebase, so the sales team is managed in one place.
"""
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import Role, User


@dataclass
class TokenClaims:
    uid: str
    email: str | None
    name: str | None
    is_anonymous: bool


_firebase_app = None


def _verify_firebase(token: str) -> TokenClaims:
    global _firebase_app
    import firebase_admin
    from firebase_admin import auth as fb_auth

    if _firebase_app is None:
        opts = {"projectId": get_settings().firebase_project_id} if get_settings().firebase_project_id else None
        _firebase_app = firebase_admin.initialize_app(options=opts)
    try:
        d = fb_auth.verify_id_token(token, app=_firebase_app, check_revoked=False)
    except Exception as e:  # noqa: BLE001 — any verification failure is a 401
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from e
    provider = (d.get("firebase") or {}).get("sign_in_provider")
    return TokenClaims(d["uid"], d.get("email"), d.get("name"), provider == "anonymous")


def _verify_dev(token: str) -> TokenClaims:
    # dev:<uid>            -> anonymous user
    # dev:<uid>:<email>    -> signed-in user
    parts = token.split(":")
    if len(parts) < 2 or parts[0] != "dev" or not parts[1]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid dev token")
    email = parts[2] if len(parts) > 2 and parts[2] else None
    return TokenClaims(parts[1], email, None, email is None)


def verify_token(token: str) -> TokenClaims:
    if get_settings().auth_mode == "firebase":
        return _verify_firebase(token)
    return _verify_dev(token)


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    claims = verify_token(authorization[7:].strip())

    user = db.scalar(select(User).where(User.firebase_uid == claims.uid))
    if user is None:
        user = User(firebase_uid=claims.uid)
        db.add(user)
    # Keep identity fields in sync with the identity provider.
    user.is_anonymous = claims.is_anonymous
    if claims.email:
        user.email = claims.email.lower()
    if claims.name and not user.full_name:
        user.full_name = claims.name
    if user.email and user.email in get_settings().admin_email_set and not claims.is_anonymous:
        user.role = Role.admin
    db.commit()
    db.refresh(user)
    return user


def require_roles(*roles: Role):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
        return user

    return dep


require_staff = require_roles(Role.sales, Role.admin)
require_admin = require_roles(Role.admin)
