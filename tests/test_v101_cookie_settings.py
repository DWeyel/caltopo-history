# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

import app.main as main_module
from app.db import Base
from app.services import COOKIE_SECURE_KEY, clear_app_setting, cookie_secure_source, effective_cookie_secure, set_app_setting
from app.version import APP_VERSION


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_v101_cookie_secure_default_and_settings_override():
    assert APP_VERSION == "1.0.1"
    db = make_db()
    assert effective_cookie_secure(db) is False
    assert cookie_secure_source(db) == "environment"
    set_app_setting(db, COOKIE_SECURE_KEY, "true")
    db.commit()
    assert effective_cookie_secure(db) is True
    assert cookie_secure_source(db) == "settings"
    clear_app_setting(db, COOKIE_SECURE_KEY)
    db.commit()
    assert effective_cookie_secure(db) is False
    assert cookie_secure_source(db) == "environment"


def _cookie_test_app():
    async def endpoint(request):
        request.session["user_id"] = 1
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", endpoint)])
    app.add_middleware(SessionMiddleware, secret_key="test-secret-key", https_only=False)
    app.add_middleware(main_module.RuntimeCookieSecureMiddleware)
    return app


def test_v101_runtime_cookie_secure_flag_changes_without_restart():
    app = _cookie_test_app()
    with TestClient(app) as client:
        main_module.cookie_secure_runtime = False
        response = client.get("/")
        assert "; secure" not in response.headers["set-cookie"].lower()
        main_module.cookie_secure_runtime = True
        response = client.get("/")
        assert "; secure" in response.headers["set-cookie"].lower()
    main_module.cookie_secure_runtime = False


def test_v101_ui_and_deployment_defaults_are_http_compatible():
    root = Path(__file__).resolve().parents[1]
    config = (root / "app/config.py").read_text()
    compose = (root / "compose.yaml").read_text()
    env_example = (root / ".env.example").read_text()
    template = (root / "app/templates/settings.html").read_text()
    assert '_bool("COOKIE_SECURE", False)' in config
    assert 'COOKIE_SECURE: "${COOKIE_SECURE:-false}"' in compose
    assert "COOKIE_SECURE=false" in env_example
    assert 'name="cookie_secure"' in template
    assert 'name="clear_cookie_secure"' in template
