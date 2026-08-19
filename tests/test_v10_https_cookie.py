# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from pathlib import Path

from app.version import APP_VERSION


def test_v10_login_warning_and_standalone_https_files():
    root = Path(__file__).resolve().parents[1]
    login = (root / "app/templates/login.html").read_text()
    docker_readme = (root / "README-DOCKER.md").read_text()
    caddyfile = (root / "Caddyfile").read_text()
    https_compose = (root / "compose.https.yaml").read_text()
    assert APP_VERSION == "0.10"
    assert "settings.cookie_secure" in login
    assert "request.url.scheme != 'https'" in login
    assert "Login sessions cannot persist" in login
    assert "COOKIE_SECURE=true" in docker_readme
    assert "Login sessions cannot work" in docker_readme
    assert "reverse_proxy caltopo-history:8765" in caddyfile
    assert "443:443" in https_compose
