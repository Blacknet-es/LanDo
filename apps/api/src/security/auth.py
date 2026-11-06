from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlmodel import Session

from src.config import settings
from src.application.users.use_cases import AccessTokenIssuer, PasswordHasher
from src.domain.users.models import User
from src.infrastructure.db.models import UserModel
from src.infrastructure.db.session import get_session

password_hash = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)


class PwdlibPasswordHasher(PasswordHasher):
    def hash(self, password: str) -> str:
        return password_hash.hash(password)

    def verify(self, password: str, hashed_password: str) -> bool:
        return password_hash.verify(password, hashed_password)


class JwtAccessTokenIssuer(AccessTokenIssuer):
    def issue(self, user_id: UUID) -> str:
        return create_access_token(user_id)


def hash_password(password: str) -> str:
    return PwdlibPasswordHasher().hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return PwdlibPasswordHasher().verify(password, hashed_password)


def create_access_token(user_id: UUID) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": str(user_id), "user_id": str(user_id), "exp": expires_at},
        settings.secret_key,
        algorithm="HS256",
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=["HS256"],
        )
        user_id = UUID(payload["user_id"])
        if payload.get("sub") != str(user_id):
            raise unauthorized
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise unauthorized from exc

    model = session.get(UserModel, user_id)
    if model is None:
        raise unauthorized
    return User(
        id=model.id,
        email=model.email,
        hashed_password=model.hashed_password,
        created_at=model.created_at,
        preferred_language=model.preferred_language,
    )
