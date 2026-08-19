# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import AppSetting, Base
from app.services import (
    CALTOPO_BASE_URL_KEY,
    CALTOPO_CREDENTIAL_ID_KEY,
    DISCOVERY_INTERVAL_SECONDS_KEY,
    FULL_VERIFY_EVERY_KEY,
    caltopo_client,
    effective_credential_secret,
    set_app_setting,
    set_credential_secret,
)
from app.version import APP_VERSION


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_v1_runtime_caltopo_settings_and_secret_are_ui_manageable():
    db = make_db()
    set_app_setting(db, CALTOPO_CREDENTIAL_ID_KEY, "ABC123")
    set_credential_secret(db, "c2VjcmV0")
    set_app_setting(db, CALTOPO_BASE_URL_KEY, "https://caltopo.com")
    set_app_setting(db, DISCOVERY_INTERVAL_SECONDS_KEY, "180")
    set_app_setting(db, FULL_VERIFY_EVERY_KEY, "12")
    db.commit()

    stored = db.get(AppSetting, "caltopo_credential_secret").value
    assert stored.startswith("fernet:v1:")
    assert "c2VjcmV0" not in stored
    assert effective_credential_secret(db) == "c2VjcmV0"
    client = caltopo_client(db)
    assert client.credential_id == "ABC123"
    assert client.credential_secret == "c2VjcmV0"
    assert client.base_url == "https://caltopo.com"


def test_v1_settings_ui_never_renders_existing_caltopo_secret():
    root = Path(__file__).resolve().parents[1]
    template = (root / "app/templates/settings.html").read_text()
    assert 'name="credential_id"' in template
    assert 'name="credential_secret"' in template
    assert 'type="password"' in template
    assert 'value="{{ credential_secret }}"' not in template
    assert 'name="discovery_interval"' in template
    assert 'name="full_verify_every_value"' in template
    assert "app_secret_configured" in template


def test_v1_installers_generate_application_secret_and_initial_password():
    root = Path(__file__).resolve().parents[1]
    entrypoint = (root / "docker/docker-entrypoint.sh").read_text()
    native = (root / "deploy/install-native-debian12.sh").read_text()
    compose = (root / "compose.yaml").read_text()
    assert APP_VERSION == "1.0"
    assert "secrets.token_hex(48)" in entrypoint
    assert "secrets.token_urlsafe(24)" in entrypoint
    assert "secrets.token_hex(48)" in native
    assert "secrets.token_urlsafe(24)" in native
    assert 'APP_SECRET_KEY_FILE: "/data/.app-secret-key"' in compose
    assert 'INITIAL_ADMIN_PASSWORD_FILE: "/data/.initial-admin-password"' in compose
    assert "APP_SECRET_KEY:?" not in compose
    assert "APP_PASSWORD:?" not in compose
