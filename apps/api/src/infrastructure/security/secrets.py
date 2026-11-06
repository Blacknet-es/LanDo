from cryptography.fernet import Fernet, InvalidToken

ENCRYPTED_PREFIX = "fernet:v1:"


class SecretDecryptionError(RuntimeError):
    pass


class SecretCipher:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode("ascii"))

    def encrypt(self, secret: str) -> str:
        return ENCRYPTED_PREFIX + self._fernet.encrypt(secret.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        if not value.startswith(ENCRYPTED_PREFIX):
            return value
        token = value.removeprefix(ENCRYPTED_PREFIX)
        try:
            return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeEncodeError) as exc:
            raise SecretDecryptionError("Unable to decrypt a stored provider key") from exc
