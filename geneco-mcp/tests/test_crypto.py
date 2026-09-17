from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from geneco_mcp.security.crypto import CredentialEncryptionError, decrypt_secret, encrypt_secret


def test_round_trip() -> None:
    key = Fernet.generate_key().decode()
    ciphertext = encrypt_secret("super-secret", key=key)
    assert ciphertext != "super-secret"
    assert decrypt_secret(ciphertext, key=key) == "super-secret"


def test_wrong_key_fails_to_decrypt() -> None:
    key = Fernet.generate_key().decode()
    other_key = Fernet.generate_key().decode()
    ciphertext = encrypt_secret("super-secret", key=key)
    with pytest.raises(CredentialEncryptionError):
        decrypt_secret(ciphertext, key=other_key)


def test_missing_key_raises_on_encrypt() -> None:
    with pytest.raises(CredentialEncryptionError):
        encrypt_secret("x", key="")


def test_missing_key_raises_on_decrypt() -> None:
    with pytest.raises(CredentialEncryptionError):
        decrypt_secret("whatever", key="")
