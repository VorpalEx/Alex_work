"""Lightweight AES-256 encryption utilities for the local SQLite auth database."""
from __future__ import annotations

import base64
import hashlib
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


_SALT_SIZE = 16
_NONCE_SIZE = 12
_KEY_ITERATIONS = 200_000


def _derive_key(password: str, salt: bytes) -> bytes:
    """PBKDF2-HMAC-SHA256 key derivation."""
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _KEY_ITERATIONS, dklen=32)


def encrypt(plaintext: str, password: str) -> str:
    """Encrypt a string and return a base64-encoded ciphertext blob."""
    salt = secrets.token_bytes(_SALT_SIZE)
    nonce = secrets.token_bytes(_NONCE_SIZE)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    blob = salt + nonce + ct
    return base64.b64encode(blob).decode()


def decrypt(ciphertext_b64: str, password: str) -> str:
    """Decrypt a base64-encoded ciphertext blob and return plaintext."""
    blob = base64.b64decode(ciphertext_b64.encode())
    salt = blob[:_SALT_SIZE]
    nonce = blob[_SALT_SIZE : _SALT_SIZE + _NONCE_SIZE]
    ct = blob[_SALT_SIZE + _NONCE_SIZE :]
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None).decode()


def hash_password(password: str) -> str:
    """Return a salted SHA-256 hash suitable for storage."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash produced by hash_password."""
    try:
        salt, hashed = stored_hash.split(":", 1)
        return secrets.compare_digest(
            hashlib.sha256((salt + password).encode()).hexdigest(), hashed
        )
    except ValueError:
        return False
