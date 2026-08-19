# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _text(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _secret_or_file(value_name: str, file_name: str, default: str) -> str:
    """Read a secret from an environment variable, then from a referenced file.

    File-based secrets allow installers/containers to generate credentials without
    leaving them in compose output or requiring the operator to hand-create them.
    An explicitly supplied environment value always takes precedence.
    """
    value = os.getenv(value_name)
    if value not in (None, ""):
        return value
    path = os.getenv(file_name, "").strip()
    if path:
        try:
            file_value = Path(path).read_text(encoding="utf-8").strip()
            if file_value:
                return file_value
        except OSError:
            pass
    return default


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:////data/caltopo-history.db")
    credential_id: str = os.getenv("CALTOPO_CREDENTIAL_ID", "")
    credential_secret: str = os.getenv("CALTOPO_CREDENTIAL_SECRET", "")
    caltopo_base_url: str = os.getenv("CALTOPO_BASE_URL", "https://caltopo.com")
    poll_interval_seconds: int = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
    discovery_interval_seconds: int = int(os.getenv("DISCOVERY_INTERVAL_SECONDS", "300"))
    full_verify_every: int = int(os.getenv("FULL_VERIFY_EVERY", "30"))
    app_username: str = os.getenv("APP_USERNAME", "admin")
    app_password: str = _secret_or_file("APP_PASSWORD", "INITIAL_ADMIN_PASSWORD_FILE", "change-me")
    initial_admin_password_file: str = os.getenv("INITIAL_ADMIN_PASSWORD_FILE", "")
    app_secret_key: str = _secret_or_file("APP_SECRET_KEY", "APP_SECRET_KEY_FILE", "change-me-to-a-long-random-string")
    app_secret_key_file: str = os.getenv("APP_SECRET_KEY_FILE", "")
    cookie_secure: bool = _bool("COOKIE_SECURE", False)
    timezone: str = os.getenv("TZ", "Europe/Berlin")
    source_code_url: str = _text("SOURCE_CODE_URL", "https://github.com/DWeyel/caltopo-history")
    map_tile_url: str = _text("MAP_TILE_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png")
    map_tile_attribution: str = _text(
        "MAP_TILE_ATTRIBUTION",
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    )
    map_tile_max_zoom: int = int(_text("MAP_TILE_MAX_ZOOM", "19"))


settings = Settings()
