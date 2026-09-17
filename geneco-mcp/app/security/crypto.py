"""Encryption at rest for stored D365 credentials.

No encryption-at-rest implementation exists anywhere in duta-ilmu (or its
sibling repos) to reuse — every "KMS/pgcrypto" mention there is an
unaddressed TODO. This is a from-scratch, deliberately simple symmetric
scheme: ``cryptography``'s ``Fernet`` (AES-128-CBC + HMAC, authenticated).

The key itself (``Settings.credential_encryption_key``) is a stopgap: a
bare env var is adequate for now since nothing better exists elsewhere in
this codebase family, but it should be swapped for a real KMS/Key
Vault-issued key before this holds real tenant secrets in production — see
the plan's "deferred security follow-up" note.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


class CredentialEncryptionError(Exception):
    """Raised when the configured key is missing/invalid, or ciphertext
    can't be decrypted with it (wrong/rotated key, or corrupted data)."""


def _fernet(key: str) -> Fernet:
    if not key:
        raise CredentialEncryptionError(
            "GENECO_MCP_CREDENTIAL_ENCRYPTION_KEY is not set — refusing to "
            "store or read credentials without encryption."
        )
    try:
        return Fernet(key.encode())
    except ValueError as exc:
        raise CredentialEncryptionError(f"invalid credential encryption key: {exc}") from exc


def encrypt_secret(plaintext: str, *, key: str) -> str:
    return _fernet(key).encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str, *, key: str) -> str:
    try:
        return _fernet(key).decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise CredentialEncryptionError("could not decrypt stored client_secret") from exc
