# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from .config import settings

PREFIX = "fernet:v1:"


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.app_secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    if not value:
        return ""
    token = _fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return PREFIX + token


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    if not value.startswith(PREFIX):
        # Accept an old/plain value if a future migration ever encounters one,
        # but all new UI writes are encrypted.
        return value
    try:
        return _fernet().decrypt(value[len(PREFIX):].encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise ValueError(
            "Stored CalTopo credential secret cannot be decrypted. "
            "If APP_SECRET_KEY was changed, re-enter the CalTopo credential secret in Settings."
        ) from exc
