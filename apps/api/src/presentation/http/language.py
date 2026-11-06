from fastapi import Depends, Request

from src.domain.users.models import User, UserLanguage
from src.security.auth import get_current_user


def _language_from_header(header: str | None) -> str | None:
    if not header:
        return None

    candidates: list[tuple[float, int, str]] = []
    for index, value in enumerate(header.split(",")):
        parts = [part.strip() for part in value.split(";")]
        language = parts[0].split("-", 1)[0].lower()
        if language not in {item.value for item in UserLanguage}:
            continue
        quality = 1.0
        for parameter in parts[1:]:
            key, separator, raw_value = parameter.partition("=")
            if separator and key.strip().lower() == "q":
                try:
                    quality = float(raw_value)
                except ValueError:
                    quality = 0.0
                break
        if 0 < quality <= 1:
            candidates.append((quality, -index, language))

    return max(candidates)[2] if candidates else None


def get_request_language(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> str:
    return (
        _language_from_header(request.headers.get("Accept-Language"))
        or current_user.preferred_language
        or UserLanguage.SPANISH.value
    )
