# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import os
from dataclasses import dataclass


def _text(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


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
    app_password: str = os.getenv("APP_PASSWORD", "change-me")
    app_secret_key: str = os.getenv("APP_SECRET_KEY", "change-me-to-a-long-random-string")
    cookie_secure: bool = _bool("COOKIE_SECURE", True)
    timezone: str = os.getenv("TZ", "Europe/Berlin")
    source_code_url: str = _text("SOURCE_CODE_URL", "https://github.com/DWeyel/caltopo-history")
    map_tile_url: str = _text("MAP_TILE_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png")
    map_tile_attribution: str = _text(
        "MAP_TILE_ATTRIBUTION",
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    )
    map_tile_max_zoom: int = int(_text("MAP_TILE_MAX_ZOOM", "19"))


settings = Settings()
