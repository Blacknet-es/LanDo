import pytest
from cryptography.fernet import Fernet

from src.infrastructure.security.secrets import (
    ENCRYPTED_PREFIX,
    SecretCipher,
    SecretDecryptionError,
)


def test_secret_cipher_encrypts_and_decrypts_provider_keys() -> None:
    cipher = SecretCipher(Fernet.generate_key().decode("ascii"))

    encrypted = cipher.encrypt("provider-secret")

    assert encrypted.startswith(ENCRYPTED_PREFIX)
    assert "provider-secret" not in encrypted
    assert cipher.decrypt(encrypted) == "provider-secret"


def test_secret_cipher_keeps_legacy_plaintext_readable_during_migration() -> None:
    cipher = SecretCipher(Fernet.generate_key().decode("ascii"))

    assert cipher.decrypt("legacy-plaintext") == "legacy-plaintext"


def test_secret_cipher_rejects_a_key_that_cannot_be_decrypted() -> None:
    first = SecretCipher(Fernet.generate_key().decode("ascii"))
    second = SecretCipher(Fernet.generate_key().decode("ascii"))

    with pytest.raises(SecretDecryptionError):
        second.decrypt(first.encrypt("provider-secret"))
