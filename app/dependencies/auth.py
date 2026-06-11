from __future__ import annotations

from fastapi import Depends, Header
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository


def _extract_token(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise UnauthorizedException("Missing Bearer token")
    return authorization.split(" ", 1)[1]


def get_current_user(
    token: str = Depends(_extract_token),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type")
        user_id = int(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise UnauthorizedException("Invalid or expired token")

    user = UserRepository(db).get_by_id(user_id)
    if not user or not user.is_active:
        raise UnauthorizedException("User not found or inactive")
    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise ForbiddenException("Admin access required")
    return current_user


def get_optional_user(
    authorization: str = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        token = authorization.split(" ", 1)[1]
        payload = decode_token(token)
        user_id = int(payload["sub"])
        return UserRepository(db).get_by_id(user_id)
    except Exception:
        return None
