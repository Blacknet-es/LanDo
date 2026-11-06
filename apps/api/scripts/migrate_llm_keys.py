from sqlmodel import Session, select

from src.config import settings
from src.infrastructure.db.models import UserSettingsModel
from src.infrastructure.db.session import engine
from src.infrastructure.security.secrets import ENCRYPTED_PREFIX, SecretCipher


def main() -> None:
    cipher = SecretCipher(settings.resolved_llm_secrets_encryption_key)
    migrated = 0
    with Session(engine) as session:
        records = session.exec(select(UserSettingsModel)).all()
        for record in records:
            keys = dict(record.api_keys or {})
            if any(not value.startswith(ENCRYPTED_PREFIX) for value in keys.values()):
                record.api_keys = {
                    provider: value if value.startswith(ENCRYPTED_PREFIX) else cipher.encrypt(value)
                    for provider, value in keys.items()
                }
                session.add(record)
                migrated += 1
        session.commit()
    print(f"Encrypted provider keys for {migrated} settings record(s).")


if __name__ == "__main__":
    main()
