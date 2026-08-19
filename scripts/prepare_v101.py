#!/usr/bin/env python3
from pathlib import Path
import re


def get(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def put(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def rep(path: str, old: str, new: str, count: int = 1) -> None:
    text = get(path)
    found = text.count(old)
    if found != count:
        raise RuntimeError(f"{path}: expected {count} match(es), found {found}: {old[:120]!r}")
    put(path, text.replace(old, new, count))


def regex_rep(path: str, pattern: str, replacement: str, flags: int = 0) -> None:
    text = get(path)
    new, n = re.subn(pattern, replacement, text, count=1, flags=flags)
    if n != 1:
        raise RuntimeError(f"{path}: regex expected one match, found {n}: {pattern[:120]!r}")
    put(path, new)


# ---------------------------------------------------------------------------
# Version and deployment defaults
# ---------------------------------------------------------------------------
rep("app/version.py", 'APP_VERSION = "1.0"', 'APP_VERSION = "1.0.1"')
rep("app/config.py", 'cookie_secure: bool = _bool("COOKIE_SECURE", True)', 'cookie_secure: bool = _bool("COOKIE_SECURE", False)')
rep("Dockerfile", 'org.opencontainers.image.version="1.0"', 'org.opencontainers.image.version="1.0.1"')
rep("compose.yaml", 'image: "${IMAGE_REF:-caltopo-history:1.0}"', 'image: "${IMAGE_REF:-caltopo-history:1.0.1}"')
rep("compose.yaml", 'COOKIE_SECURE: "${COOKIE_SECURE:-true}"', 'COOKIE_SECURE: "${COOKIE_SECURE:-false}"')

env = get(".env.example").replace("Optional here: v1.0 can be started first", "Optional here: v1.0.1 can be started first")
env_old = (
    "# IMPORTANT: COOKIE_SECURE=true requires the browser to access CalTopo History via HTTPS.\n"
    "# If you open http://host:8765 with COOKIE_SECURE=true, valid credentials will not create\n"
    "# a usable login session because browsers do not send Secure cookies over HTTP.\n"
    "# Keep true for production. Set false ONLY for temporary local/test HTTP access.\n"
    "COOKIE_SECURE=true"
)
env_new = (
    "# Default: false, so a fresh installation works over HTTP as well as HTTPS.\n"
    "# For an HTTPS deployment, enable Secure session cookies in Settings or set this to true.\n"
    "# A value saved in Settings overrides this deployment fallback until the override is reset.\n"
    "COOKIE_SECURE=false"
)
if env.count(env_old) != 1:
    raise RuntimeError(".env.example: legacy COOKIE_SECURE block not found")
put(".env.example", env.replace(env_old, env_new, 1))

rep(
    "deploy/caltopo-history.env.example",
    "# IMPORTANT: true requires HTTPS at the browser-facing URL.\nCOOKIE_SECURE=true",
    "# Default: false so HTTP works out of the box. Enable for HTTPS deployments if desired.\n"
    "# A Settings-UI override takes precedence over this environment fallback.\nCOOKIE_SECURE=false",
)

# ---------------------------------------------------------------------------
# Persistent COOKIE_SECURE setting
# ---------------------------------------------------------------------------
rep(
    "app/services.py",
    'FULL_VERIFY_EVERY_KEY = "full_verify_every"\n',
    'FULL_VERIFY_EVERY_KEY = "full_verify_every"\nCOOKIE_SECURE_KEY = "cookie_secure"\n',
)

rep(
    "app/services.py",
    "def set_app_setting(db: Session, key: str, value: str) -> None:\n"
    "    row = db.get(AppSetting, key)\n"
    "    if row is None:\n"
    "        db.add(AppSetting(key=key, value=value))\n"
    "    else:\n"
    "        row.value = value\n\n\n\n"
    "def effective_credential_id",
    "def set_app_setting(db: Session, key: str, value: str) -> None:\n"
    "    row = db.get(AppSetting, key)\n"
    "    if row is None:\n"
    "        db.add(AppSetting(key=key, value=value))\n"
    "    else:\n"
    "        row.value = value\n\n\n"
    "def clear_app_setting(db: Session, key: str) -> None:\n"
    "    row = db.get(AppSetting, key)\n"
    "    if row is not None:\n"
    "        db.delete(row)\n\n\n"
    "def effective_credential_id",
)

rep(
    "app/services.py",
    "def full_verify_every(db: Session) -> int:\n"
    "    try:\n"
    "        return max(1, int(get_app_setting(db, FULL_VERIFY_EVERY_KEY, str(settings.full_verify_every))))\n"
    "    except (TypeError, ValueError):\n"
    "        return max(1, settings.full_verify_every)\n\n\n"
    "def caltopo_client",
    "def full_verify_every(db: Session) -> int:\n"
    "    try:\n"
    "        return max(1, int(get_app_setting(db, FULL_VERIFY_EVERY_KEY, str(settings.full_verify_every))))\n"
    "    except (TypeError, ValueError):\n"
    "        return max(1, settings.full_verify_every)\n\n\n"
    "def effective_cookie_secure(db: Session) -> bool:\n"
    "    row = db.get(AppSetting, COOKIE_SECURE_KEY)\n"
    "    if row is None:\n"
    "        return settings.cookie_secure\n"
    "    raw = row.value.strip().lower()\n"
    "    if raw in {\"1\", \"true\", \"yes\", \"on\"}:\n"
    "        return True\n"
    "    if raw in {\"0\", \"false\", \"no\", \"off\"}:\n"
    "        return False\n"
    "    return settings.cookie_secure\n\n\n"
    "def cookie_secure_source(db: Session) -> str:\n"
    "    return \"settings\" if db.get(AppSetting, COOKIE_SECURE_KEY) is not None else \"environment\"\n\n\n"
    "def caltopo_client",
)

# ---------------------------------------------------------------------------
# Runtime session-cookie policy
# ---------------------------------------------------------------------------
rep("app/main.py", "    CALTOPO_CREDENTIAL_ID_KEY,\n    DISCOVERY_INTERVAL_SECONDS_KEY,", "    CALTOPO_CREDENTIAL_ID_KEY,\n    COOKIE_SECURE_KEY,\n    DISCOVERY_INTERVAL_SECONDS_KEY,")
rep("app/main.py", "    credential_secret_source,\n    discovery_interval_seconds,", "    credential_secret_source,\n    cookie_secure_source,\n    discovery_interval_seconds,")
rep("app/main.py", "    effective_caltopo_base_url,\n    effective_credential_id,", "    effective_caltopo_base_url,\n    effective_cookie_secure,\n    effective_credential_id,")
rep("app/main.py", "    refresh_team_catalog,\n    clear_credential_secret_override,", "    refresh_team_catalog,\n    clear_app_setting,\n    clear_credential_secret_override,")

old_globals = (
    "stop_event = asyncio.Event()\n"
    "ROLES = {\"admin\", \"user\", \"view\"}\n"
    "LOCAL_TZ = ZoneInfo(settings.timezone)\n\n\n"
    "@asynccontextmanager\n"
    "async def lifespan(app: FastAPI):\n"
    "    init_db()\n"
    "    task = asyncio.create_task(scheduler_loop(stop_event))"
)
new_globals = '''stop_event = asyncio.Event()
ROLES = {"admin", "user", "view"}
LOCAL_TZ = ZoneInfo(settings.timezone)
SESSION_COOKIE_NAME = "session"
cookie_secure_runtime = settings.cookie_secure


class RuntimeCookieSecureMiddleware:
    """Apply the effective cookie policy without requiring an application restart."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_cookie_policy(message):
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers", []))
                changed = False
                prefix = (SESSION_COOKIE_NAME + "=").encode("latin-1")
                for index, (name, value) in enumerate(headers):
                    if name.lower() != b"set-cookie" or not value.lower().startswith(prefix):
                        continue
                    parts = [part.strip() for part in value.decode("latin-1").split(";")]
                    parts = [part for part in parts if part.lower() != "secure"]
                    if cookie_secure_runtime:
                        parts.append("Secure")
                    headers[index] = (name, "; ".join(parts).encode("latin-1"))
                    changed = True
                if changed:
                    message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_cookie_policy)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global cookie_secure_runtime
    init_db()
    with SessionLocal() as db:
        cookie_secure_runtime = effective_cookie_secure(db)
    task = asyncio.create_task(scheduler_loop(stop_event))'''
rep("app/main.py", old_globals, new_globals)

rep(
    "app/main.py",
    "app.add_middleware(\n"
    "    SessionMiddleware,\n"
    "    secret_key=settings.app_secret_key,\n"
    "    https_only=settings.cookie_secure,\n"
    "    same_site=\"lax\",\n"
    "    max_age=12 * 60 * 60,\n"
    ")\n"
    "app.mount",
    "app.add_middleware(\n"
    "    SessionMiddleware,\n"
    "    secret_key=settings.app_secret_key,\n"
    "    https_only=False,\n"
    "    same_site=\"lax\",\n"
    "    max_age=12 * 60 * 60,\n"
    ")\n"
    "app.add_middleware(RuntimeCookieSecureMiddleware)\n"
    "app.mount",
)

rep(
    "app/main.py",
    '        "settings": settings,\n        "app_version": APP_VERSION,',
    '        "settings": settings,\n        "cookie_secure": cookie_secure_runtime,\n        "app_version": APP_VERSION,',
)
rep(
    "app/main.py",
    "            cookie_secure=settings.cookie_secure,\n            timezone=settings.timezone,",
    "            cookie_secure=effective_cookie_secure(db),\n"
    "            cookie_secure_source=cookie_secure_source(db),\n"
    "            timezone=settings.timezone,",
)

# Settings POST handler.
rep(
    "app/main.py",
    "    full_verify_every_value: int = Form(30),\n"
    "    db: Session = Depends(get_db),\n"
    "):\n"
    "    if global_interval_minutes",
    "    full_verify_every_value: int = Form(30),\n"
    "    cookie_secure: str = Form(\"false\"),\n"
    "    clear_cookie_secure: str | None = Form(None),\n"
    "    db: Session = Depends(get_db),\n"
    "):\n"
    "    global cookie_secure_runtime\n\n"
    "    if global_interval_minutes",
)

rep(
    "app/main.py",
    "    if full_verify_every_value < 1 or full_verify_every_value > 10000:\n"
    "        flash_t(request, db, \"invalid_full_verify\", \"danger\")\n"
    "        return RedirectResponse(\"/settings\", status_code=303)\n\n"
    "    ui_language = normalize_language(ui_language)",
    "    if full_verify_every_value < 1 or full_verify_every_value > 10000:\n"
    "        flash_t(request, db, \"invalid_full_verify\", \"danger\")\n"
    "        return RedirectResponse(\"/settings\", status_code=303)\n"
    "    if cookie_secure not in {\"true\", \"false\"}:\n"
    "        flash_t(request, db, \"invalid_cookie_secure\", \"danger\")\n"
    "        return RedirectResponse(\"/settings\", status_code=303)\n\n"
    "    ui_language = normalize_language(ui_language)",
)

rep(
    "app/main.py",
    "    set_app_setting(db, FULL_VERIFY_EVERY_KEY, str(full_verify_every_value))\n"
    "    if clear_credential_secret:",
    "    set_app_setting(db, FULL_VERIFY_EVERY_KEY, str(full_verify_every_value))\n"
    "    if clear_cookie_secure:\n"
    "        clear_app_setting(db, COOKIE_SECURE_KEY)\n"
    "    else:\n"
    "        set_app_setting(db, COOKIE_SECURE_KEY, cookie_secure)\n"
    "    db.flush()\n"
    "    cookie_secure_runtime = effective_cookie_secure(db)\n"
    "    if clear_credential_secret:",
)

rep(
    "app/main.py",
    '            f"disk_hard_mb={disk_hard_mb}, ui_language={ui_language}"',
    '            f"disk_hard_mb={disk_hard_mb}, ui_language={ui_language}, "\n'
    '            f"cookie_secure={\'environment\' if clear_cookie_secure else cookie_secure}"',
)

# ---------------------------------------------------------------------------
# Settings UI and login warning
# ---------------------------------------------------------------------------
settings_html = get("app/templates/settings.html")
marker = "    </fieldset>\n\n    <fieldset class=\"settings-fieldset\">\n      <legend>{{ t('language') }}</legend>"
insert = '''    </fieldset>

    <fieldset class="settings-fieldset">
      <legend>{{ t('session_security') }}</legend>
      <label>{{ t('cookie_secure_status') }}
        <select name="cookie_secure" required>
          <option value="false" {% if not cookie_secure %}selected{% endif %}>{{ t('cookie_secure_http_option') }}</option>
          <option value="true" {% if cookie_secure %}selected{% endif %}>{{ t('cookie_secure_https_option') }}</option>
        </select>
      </label>
      <p class="hint">{{ t('cookie_secure_help') }} · {{ t('configuration_source', source=t('source_settings') if cookie_secure_source == 'settings' else t('source_environment')) }}</p>
      {% if cookie_secure_source == 'settings' %}
      <label class="check-row"><input type="checkbox" name="clear_cookie_secure" value="1"> {{ t('cookie_secure_use_environment') }}</label>
      {% endif %}
    </fieldset>

    <fieldset class="settings-fieldset">
      <legend>{{ t('language') }}</legend>'''
if settings_html.count(marker) != 1:
    raise RuntimeError("settings.html: language fieldset marker not found exactly once")
settings_html = settings_html.replace(marker, insert, 1)
old_row = "    <div><dt>{{ t('cookie_secure_status') }}</dt><dd><strong>{{ t('enabled') if cookie_secure else t('disabled') }}</strong></dd></div>"
new_row = "    <div><dt>{{ t('cookie_secure_status') }}</dt><dd><strong>{{ t('enabled') if cookie_secure else t('disabled') }}</strong> · {{ t('configuration_source', source=t('source_settings') if cookie_secure_source == 'settings' else t('source_environment')) }}</dd></div>"
if settings_html.count(old_row) != 1:
    raise RuntimeError("settings.html: cookie status row not found exactly once")
put("app/templates/settings.html", settings_html.replace(old_row, new_row, 1))

rep(
    "app/templates/login.html",
    "{% if settings.cookie_secure and request.url.scheme != 'https' %}",
    "{% if cookie_secure and request.url.scheme != 'https' %}",
)
login = get("app/templates/login.html")
login = login.replace(
    "Verwende HTTPS oder setze <code>COOKIE_SECURE=false</code> ausschließlich für eine temporäre lokale/Test-Installation.",
    "Verwende HTTPS oder deaktiviere Secure Session Cookies in den Settings bzw. über <code>COOKIE_SECURE=false</code>.",
)
login = login.replace(
    "Use HTTPS, or set <code>COOKIE_SECURE=false</code> only for a temporary local/test deployment.",
    "Use HTTPS, or disable Secure session cookies in Settings or with <code>COOKIE_SECURE=false</code>.",
)
put("app/templates/login.html", login)

# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------
i18n = get("app/i18n.py")
en_old = (
    '        "cookie_secure_status": "Secure session cookie (COOKIE_SECURE)",\n'
    '        "cookie_secure_help": "When enabled, users must access the application through HTTPS. This is a deployment setting and requires a restart to change.",\n'
    '        "timezone_setting": "Application timezone",\n'
    '        "deployment_only": "Deployment setting; change it in the environment/secret file and restart the service.",'
)
en_new = (
    '        "session_security": "Session security",\n'
    '        "cookie_secure_status": "Secure session cookie (COOKIE_SECURE)",\n'
    '        "cookie_secure_http_option": "Disabled — HTTP and HTTPS logins allowed",\n'
    '        "cookie_secure_https_option": "Enabled — HTTPS required",\n'
    '        "cookie_secure_use_environment": "Remove the Settings override and use COOKIE_SECURE from the deployment environment",\n'
    '        "cookie_secure_help": "Disabled is the 1.0.1 default so HTTP works out of the box. Enable this for HTTPS deployments to mark session cookies Secure. Changes take effect immediately; enabling it while using HTTP ends the usable HTTP login session.",\n'
    '        "timezone_setting": "Application timezone",\n'
    '        "deployment_only": "The application secret key and timezone remain deployment-level settings.",'
)
if i18n.count(en_old) != 1:
    raise RuntimeError("i18n.py: English cookie block not found exactly once")
i18n = i18n.replace(en_old, en_new, 1)

de_old = (
    '        "cookie_secure_status": "Secure Session Cookie (COOKIE_SECURE)",\n'
    '        "cookie_secure_help": "Wenn aktiviert, muss die Anwendung über HTTPS aufgerufen werden. Dies ist eine Deployment-Einstellung und erfordert für Änderungen einen Neustart.",\n'
    '        "timezone_setting": "Anwendungs-Zeitzone",\n'
    '        "deployment_only": "Deployment-Einstellung; in Environment/Secret-Datei ändern und Service neu starten.",'
)
de_new = (
    '        "session_security": "Session-Sicherheit",\n'
    '        "cookie_secure_status": "Secure Session Cookie (COOKIE_SECURE)",\n'
    '        "cookie_secure_http_option": "Deaktiviert — Anmeldung über HTTP und HTTPS möglich",\n'
    '        "cookie_secure_https_option": "Aktiviert — HTTPS erforderlich",\n'
    '        "cookie_secure_use_environment": "Settings-Override entfernen und COOKIE_SECURE aus der Deployment-Umgebung verwenden",\n'
    '        "cookie_secure_help": "Deaktiviert ist der Standard ab 1.0.1, damit HTTP ohne weitere Konfiguration funktioniert. Für HTTPS-Deployments kann Secure für Session-Cookies aktiviert werden. Änderungen wirken sofort; eine Aktivierung während HTTP genutzt wird beendet die nutzbare HTTP-Session.",\n'
    '        "timezone_setting": "Anwendungs-Zeitzone",\n'
    '        "deployment_only": "Application Secret Key und Zeitzone bleiben Deployment-Einstellungen.",'
)
if i18n.count(de_old) != 1:
    raise RuntimeError("i18n.py: German cookie block not found exactly once")
i18n = i18n.replace(de_old, de_new, 1)

needle = '        "invalid_full_verify": "Full verification interval must be between 1 and 10000 polls.",'
if i18n.count(needle) != 1:
    raise RuntimeError("i18n.py: English validation marker missing")
i18n = i18n.replace(needle, needle + '\n        "invalid_cookie_secure": "COOKIE_SECURE must be enabled or disabled.",', 1)

needle = '        "invalid_full_verify": "Das Full-Verification-Intervall muss zwischen 1 und 10000 Polls liegen.",'
if i18n.count(needle) != 1:
    raise RuntimeError("i18n.py: German validation marker missing")
i18n = i18n.replace(needle, needle + '\n        "invalid_cookie_secure": "COOKIE_SECURE muss aktiviert oder deaktiviert sein.",', 1)
put("app/i18n.py", i18n)

# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------
for path in ("README.md", "README-DOCKER.md", "README-DEBIAN-ISPConfig.md"):
    put(path, get(path).replace("1.0", "1.0.1"))

readme = get("README.md")
readme = readme.replace(
    "- UI language and disk-space protection thresholds.",
    "- UI language and disk-space protection thresholds;\n- Secure session-cookie policy (`COOKIE_SECURE`), with immediate runtime effect.",
)
readme = readme.replace(
    "`APP_SECRET_KEY`, `COOKIE_SECURE` and the application timezone remain deployment-level settings. Settings shows their status/current value where appropriate, but changing them requires updating the deployment environment/secret file and restarting the application.",
    "`APP_SECRET_KEY` and the application timezone remain deployment-level settings. `COOKIE_SECURE` can be changed in Settings; a saved UI value overrides the deployment environment until the override is reset.",
)
readme, n = re.subn(
    r"## HTTPS / secure-cookie warning\n\n.*?\n\n## Container compliance",
    """## HTTPS / secure-cookie behavior

CalTopo History 1.0.1 defaults to `COOKIE_SECURE=false`, so a fresh installation can be used over HTTP immediately. This is convenient for local, LAN and reverse-proxy setup before TLS is configured.

For an HTTPS deployment, enable **Settings → Session security → Secure session cookie** (or set `COOKIE_SECURE=true` in the deployment environment before a Settings override exists). When enabled, browsers will send the session cookie only over HTTPS. The Settings change takes effect immediately and can be reset to the deployment-environment value.

HTTPS remains recommended for Internet-facing deployments because `COOKIE_SECURE=false` does not protect the session cookie from being sent over an unencrypted HTTP connection.

## Container compliance""",
    readme,
    count=1,
    flags=re.S,
)
if n != 1:
    raise RuntimeError("README.md: HTTPS section not found")
put("README.md", readme)

docker_doc = get("README-DOCKER.md")
docker_doc, n = re.subn(
    r"## HTTPS and login cookies — important\n\n.*?\n\n### Option A: existing reverse proxy",
    """## HTTPS and login cookies — important

The 1.0.1 default is:

```dotenv
COOKIE_SECURE=false
```

This allows a fresh installation to authenticate over either HTTP or HTTPS. For an Internet-facing HTTPS deployment, enable Secure session cookies under **Settings → Session security**, or set `COOKIE_SECURE=true` in `.env` before a Settings override exists.

A value saved in Settings overrides the `.env` fallback and takes effect immediately. Use the **use deployment environment** option in Settings to remove the override. If Secure cookies are enabled while the browser is using HTTP, the HTTP login session will no longer be usable; switch to the HTTPS URL.

HTTPS is still recommended for Internet-facing deployments. With `COOKIE_SECURE=false`, HTTP transports the session cookie without TLS protection.

### Option A: existing reverse proxy""",
    docker_doc,
    count=1,
    flags=re.S,
)
if n != 1:
    raise RuntimeError("README-DOCKER.md: HTTPS section not found")
put("README-DOCKER.md", docker_doc)

debian_doc = get("README-DEBIAN-ISPConfig.md")
debian_doc, n = re.subn(
    r"### Important: `COOKIE_SECURE` and HTTPS\n\n.*?\n\n`POLL_INTERVAL_SECONDS`",
    """### Important: `COOKIE_SECURE` and HTTPS

1.0.1 defaults to `COOKIE_SECURE=false`, so the application can be used over HTTP immediately after installation. For an Internet-facing ISPConfig/Apache HTTPS deployment, enable Secure session cookies under **Settings → Session security**, or set `COOKIE_SECURE=true` in `/etc/caltopo-history.env` before a Settings override exists.

A Settings value overrides the environment fallback and takes effect immediately. Reset the Settings override to return control to `/etc/caltopo-history.env`. If Secure cookies are enabled while the browser is using HTTP, switch to the HTTPS URL for subsequent requests.

Keep port 8765 private whenever a reverse proxy is used. HTTPS remains recommended for Internet-facing deployments.

`POLL_INTERVAL_SECONDS`""",
    debian_doc,
    count=1,
    flags=re.S,
)
if n != 1:
    raise RuntimeError("README-DEBIAN-ISPConfig.md: COOKIE_SECURE section not found")
debian_doc = debian_doc.replace(
    "- disk-space protection thresholds\n- Users",
    "- disk-space protection thresholds\n- Secure session-cookie policy (`COOKIE_SECURE`)\n- Users",
)
put("README-DEBIAN-ISPConfig.md", debian_doc)

# ---------------------------------------------------------------------------
# Tests and release notes
# ---------------------------------------------------------------------------
for path in ("tests/test_v10_https_cookie.py", "tests/test_v1_settings_install.py"):
    text = get(path).replace('assert APP_VERSION == "1.0"', 'assert APP_VERSION == "1.0.1"')
    if path.endswith("test_v10_https_cookie.py"):
        text = text.replace('assert "settings.cookie_secure" in login', 'assert "cookie_secure" in login')
    put(path, text)

put(
    "tests/test_v101_cookie_settings.py",
    '''# SPDX-FileCopyrightText: 2026 Dennis Weyel
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
''',
)

put(
    "RELEASE-NOTES-v1.0.1.md",
    '''# CalTopo History 1.0.1

Patch release focused on HTTP-first installation behavior and session-cookie configuration.

## Changes

- `COOKIE_SECURE` now defaults to `false` for fresh Docker and native Debian installations, so login works over plain HTTP without pre-configuration.
- Added an administrator setting for the Secure session-cookie flag under **Settings → Session security**.
- A Settings value overrides the deployment environment and can be reset back to the environment fallback.
- Changes to the Secure cookie policy take effect immediately for newly written session cookies; no container or service restart is required.
- Enabling Secure cookies while using an HTTP URL intentionally makes subsequent HTTP session requests unusable; switch to HTTPS.
- Updated Docker, Debian/ISPConfig and general documentation for the new default and override behavior.

## Security note

`COOKIE_SECURE=false` improves out-of-box compatibility but does not provide transport protection for the session cookie on plain HTTP. HTTPS with Secure session cookies remains recommended for Internet-facing deployments.
''',
)

print("v1.0.1 patch prepared")
