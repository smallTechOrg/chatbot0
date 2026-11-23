"""
Encryption for credentials stored in the database (WhatsApp access tokens and
app secrets), and the key that signs the admin login cookie.

Both keys come from CHATBOT0_SECRET_KEY, each derived for its own purpose, so
the cookie key can never decrypt a token. Changing CHATBOT0_SECRET_KEY makes
stored tokens unreadable: they then have to be entered again.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from core import config


class SecretKeyMissing(RuntimeError):
    """CHATBOT0_SECRET_KEY is not set."""


def _derive(purpose: str) -> bytes:
    if not config.CHATBOT0_SECRET_KEY:
        raise SecretKeyMissing("CHATBOT0_SECRET_KEY is not set (see .env.example)")
    return hashlib.sha256(f"chatbot0:{purpose}:{config.CHATBOT0_SECRET_KEY}".encode()).digest()


def _fernet() -> Fernet:
    return Fernet(base64.urlsafe_b64encode(_derive("credential-encryption")))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    """The plain value. Raises InvalidToken when the key changed since it was stored."""
    return _fernet().decrypt(token.encode()).decode()


def session_signing_key() -> bytes:
    return _derive("admin-session")


__all__ = ["InvalidToken", "SecretKeyMissing", "decrypt", "encrypt", "session_signing_key"]
