from fastapi.testclient import TestClient
from sqlmodel import Session

from src.domain.users.models import User
from src.infrastructure.db.models import UserModel
from src.main import app
from src.security.auth import create_access_token


def create_test_user(session: Session, email: str = "test@example.com") -> User:
    user = User(email=email, hashed_password="unused-test-password-hash")
    model = UserModel(
        id=user.id,
        email=user.email,
        hashed_password=user.hashed_password,
        created_at=user.created_at,
    )
    session.add(model)
    session.commit()
    session.refresh(model)
    session.info["test_user_id"] = model.id
    return user


def authenticated_client(session: Session) -> TestClient:
    user_id = session.info.get("test_user_id")
    if user_id is None:
        user_id = create_test_user(session).id
    token = create_access_token(user_id)
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


def get_test_user_id(session: Session):
    user_id = session.info.get("test_user_id")
    if user_id is None:
        user_id = create_test_user(session).id
    return user_id
