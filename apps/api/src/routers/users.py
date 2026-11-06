from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.application.users.use_cases import InvalidUserLanguage, UpdateUserLanguageUseCase
from src.domain.users.models import User, UserLanguage
from src.presentation.http.dependencies import get_update_user_language_use_case
from src.security.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


class UserProfileResponse(BaseModel):
    id: str
    email: str
    preferred_language: UserLanguage
    created_at: datetime


class UpdateUserProfileRequest(BaseModel):
    preferred_language: UserLanguage


@router.get("/me", response_model=UserProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)) -> UserProfileResponse:
    return UserProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        preferred_language=current_user.preferred_language,
        created_at=current_user.created_at,
    )


@router.patch("/me", response_model=UserProfileResponse)
def update_profile(
    payload: UpdateUserProfileRequest,
    current_user: User = Depends(get_current_user),
    use_case: UpdateUserLanguageUseCase = Depends(get_update_user_language_use_case),
) -> UserProfileResponse:
    try:
        user = use_case.execute(current_user.id, payload.preferred_language.value)
    except InvalidUserLanguage as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported preferred language",
        ) from exc
    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        preferred_language=user.preferred_language,
        created_at=user.created_at,
    )
