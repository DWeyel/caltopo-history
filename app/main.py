# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import asyncio
import json
import os
import re
from contextlib import asynccontextmanager
from datetime import timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

from jinja2 import pass_context

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .auth import hash_password, verify_password
from .config import settings
from .db import AuditLog, AppUser, MapWatch, ObjectVersion, SessionLocal, Snapshot, TeamRule, init_db, utcnow
from .history import compare_states, current_state, diff_states, normalize_state, object_overview, snapshot_state, unpack_json
from .i18n import DEFAULT_LANGUAGE, language_options, normalize_language, translate
from .maintenance import (
    delete_database_backup,
    map_storage,
    prune_object_versions,
    prune_snapshots,
    purge_archived_map,
    storage_overview,
    vacuum_database,
)
from .scheduler import scheduler_loop
from .services import (
    AUTO_PAUSE_DAYS,
    CALTOPO_BASE_URL_KEY,
    CALTOPO_CREDENTIAL_ID_KEY,
    DISCOVERY_INTERVAL_SECONDS_KEY,
    FULL_VERIFY_EVERY_KEY,
    DISK_HARD_MB_KEY,
    DISK_WARNING_MB_KEY,
    GLOBAL_POLL_KEY,
    TEAM_ID_KEY,
    UI_LANGUAGE_KEY,
    add_audit,
    backup_watch,
    build_catalog_tree,
    configured_team_id,
    caltopo_client,
    credential_id_source,
    credential_secret_source,
    discovery_interval_seconds,
    effective_caltopo_base_url,
    effective_credential_id,
    effective_credential_secret,
    full_verify_every,
    current_disk_status,
    discover_rule,
    disk_hard_free_mb,
    disk_warning_free_mb,
    effective_poll_interval_seconds,
    ensure_watch,
    get_app_setting,
    global_poll_interval_seconds,
    refresh_team_catalog,
    clear_credential_secret_override,
    restore_one_version,
    restore_snapshot,
    set_app_setting,
    set_credential_secret,
)
from .version import APP_VERSION
from .storage_guard import DiskSpaceBlocked


stop_event = asyncio.Event()
ROLES = {"admin", "user", "view"}
LOCAL_TZ = ZoneInfo(settings.timezone)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(scheduler_loop(stop_event))
    yield
    stop_event.set()
    await task


app = FastAPI(title=f"CalTopo History v{APP_VERSION}", version=APP_VERSION, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.app_secret_key,
    https_only=settings.cookie_secure,
    same_site="lax",
    max_age=12 * 60 * 60,
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def format_localtime(value, language: str = "de") -> str:
    """Format a timestamp in Europe/Berlin.

    The direct-call default remains German for backward compatibility with earlier
    application tests. Jinja rendering uses the configured UI language via the
    context-aware wrapper below.
    """
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    local = value.astimezone(LOCAL_TZ)
    lang = normalize_language(language)
    fmt = "%d.%m.%Y %H:%M:%S %Z" if lang == "de" else "%Y-%m-%d %H:%M:%S %Z"
    return local.strftime(fmt)


@pass_context
def format_localtime_filter(context, value) -> str:
    return format_localtime(value, context.get("language", DEFAULT_LANGUAGE))


templates.env.filters["localtime"] = format_localtime_filter


def human_bytes(value) -> str:
    try:
        size = float(value or 0)
    except (TypeError, ValueError):
        size = 0.0
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"


templates.env.filters["bytesize"] = human_bytes


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_auth(request: Request, db: Session = Depends(get_db)) -> AppUser:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(303, headers={"Location": "/login"})
    user = db.get(AppUser, int(user_id))
    if not user or not user.active:
        request.session.clear()
        raise HTTPException(303, headers={"Location": "/login"})
    request.state.user = user
    return user


def require_roles(*roles: str):
    allowed = set(roles)

    def dependency(user: AppUser = Depends(require_auth)) -> AppUser:
        if user.role not in allowed:
            raise HTTPException(403, detail=translate(current_ui_language(), "permission_denied"))
        return user

    return dependency


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded[:80]
    return (request.client.host if request.client else "")[:80]


def current_ui_language(db: Session | None = None) -> str:
    if db is not None:
        return normalize_language(get_app_setting(db, UI_LANGUAGE_KEY, DEFAULT_LANGUAGE))
    try:
        with SessionLocal() as session:
            return normalize_language(get_app_setting(session, UI_LANGUAGE_KEY, DEFAULT_LANGUAGE))
    except Exception:
        return DEFAULT_LANGUAGE


def tr(db: Session | None, key: str, **kwargs) -> str:
    return translate(current_ui_language(db), key, **kwargs)


def enum_label(language: str, prefix: str, value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return "—"
    key = f"{prefix}_{raw.lower().replace('-', '_').replace(' ', '_')}"
    translated = translate(language, key)
    return raw if translated == key else translated


def friendly_error(db: Session | None, exc: Exception) -> str:
    if isinstance(exc, DiskSpaceBlocked):
        return tr(
            db, "disk_space_blocked_detail",
            free=human_bytes(exc.free_bytes), limit=human_bytes(exc.hard_free_bytes),
        )
    return str(exc)


def flash(request: Request, text: str, level: str = "info") -> None:
    request.session["flash"] = {"text": text, "level": level}


def flash_t(request: Request, db: Session | None, key: str, level: str = "info", **kwargs) -> None:
    flash(request, tr(db, key, **kwargs), level)


def ctx(request: Request, **kwargs):
    language = current_ui_language()
    base = {
        "request": request,
        "flash": request.session.pop("flash", None),
        "settings": settings,
        "app_version": APP_VERSION,
        "current_user": getattr(request.state, "user", None),
        "language": language,
        "language_options": language_options(),
        "t": lambda key, **params: translate(language, key, **params),
        "source_label": lambda value: enum_label(language, "source", value),
        "reason_label": lambda value: enum_label(language, "reason", value),
        "audit_action_label": lambda value: enum_label(language, "audit", value),
    }
    base.update(kwargs)
    return base


def _valid_map_id(raw: str) -> str | None:
    map_id = raw.strip().rstrip("/").split("/")[-1].split("?")[0]
    return map_id if re.fullmatch(r"[A-Za-z0-9_-]{3,32}", map_id) else None


def _last_admin_guard(db: Session, target: AppUser, new_role: str | None = None, new_active: bool | None = None) -> bool:
    if target.role != "admin" or not target.active:
        return False
    losing_admin = new_role is not None and new_role != "admin"
    being_disabled = new_active is False
    if not losing_admin and not being_disabled:
        return False
    active_admins = db.scalar(select(func.count()).select_from(AppUser).where(and_(AppUser.role == "admin", AppUser.active.is_(True)))) or 0
    return active_admins <= 1


@app.get("/healthz")
def healthz():
    return {"ok": True, "version": APP_VERSION}


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", ctx(request))


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.scalar(select(AppUser).where(AppUser.username == username.strip()))
    if user and user.active and verify_password(password, user.password_hash):
        user.last_login_at = utcnow()
        db.commit()
        request.session.clear()
        request.session["user_id"] = user.id
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", ctx(request, error=tr(db, "login_failed")), status_code=401)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    watches = db.scalars(select(MapWatch).order_by(MapWatch.title, MapWatch.map_id)).all()
    rules = db.scalars(select(TeamRule).order_by(TeamRule.id)).all() if user.role == "admin" else []
    audits = db.scalars(
        select(AuditLog).where(AuditLog.action.like("restore%"))
        .order_by(desc(AuditLog.created_at)).limit(10)
    ).all() if user.role == "admin" else []
    global_interval = global_poll_interval_seconds(db)
    storage = storage_overview(db)
    disk = current_disk_status(db)
    storage_by_map = {row.map_id: row for row in storage.maps}
    for watch in watches:
        watch.effective_interval_seconds = effective_poll_interval_seconds(db, watch)
        watch.storage = storage_by_map.get(watch.map_id)
    return templates.TemplateResponse(
        request, "dashboard.html", ctx(
            request, watches=watches, rules=rules, audits=audits, storage=storage, disk=disk,
            global_interval_seconds=global_interval,
        )
    )


@app.post("/maps", dependencies=[Depends(require_roles("admin", "user"))])
async def add_map(
    request: Request,
    map_id: str = Form(...),
    map_title: str = Form(""),
    db: Session = Depends(get_db),
):
    parsed = _valid_map_id(map_id)
    if not parsed:
        flash_t(request, db, "invalid_map_id", "danger")
        return RedirectResponse("/", status_code=303)
    watch = await ensure_watch(db, parsed, title=map_title.strip(), reactivate=True)
    db.commit()

    # If a root team is configured, use the documented account catalog to resolve the authoritative title.
    team_id = configured_team_id(db)
    if team_id:
        try:
            await refresh_team_catalog(db, team_id)
            db.refresh(watch)
        except Exception:
            pass

    try:
        await backup_watch(db, watch, force_full=True, reason="initial")
        flash_t(request, db, "map_now_backed_up", "success", name=watch.title or parsed)
    except Exception as exc:
        flash_t(request, db, "map_added_initial_failed", "danger", error=friendly_error(db, exc))
    return RedirectResponse("/", status_code=303)


@app.get("/maps/picker", response_class=HTMLResponse, dependencies=[Depends(require_roles("admin", "user"))])
async def map_picker(request: Request, db: Session = Depends(get_db)):
    team_id = configured_team_id(db)
    maps: list[dict] = []
    error = None
    if team_id:
        try:
            maps = await refresh_team_catalog(db, team_id)
        except Exception as exc:
            error = str(exc)
    else:
        error = tr(db, "team_id_missing_admin")
    watched_rows = db.scalars(select(MapWatch)).all()
    watched = {row.map_id for row in watched_rows}
    tree = build_catalog_tree(maps)
    duplicate_groups: dict[str, list[dict]] = {}
    for item in maps:
        if item.get("same_title_count", 1) > 1:
            duplicate_groups.setdefault(item["title"].strip().casefold(), []).append(item)
    duplicates = sorted(duplicate_groups.values(), key=lambda group: group[0]["title"].casefold())
    return templates.TemplateResponse(
        request, "map_picker.html", ctx(
            request, maps=maps, tree=tree, duplicates=duplicates, team_id=team_id, watched=watched, error=error
        )
    )


@app.get("/api/maps/{map_id}/preview", dependencies=[Depends(require_roles("admin", "user"))])
async def map_picker_preview(map_id: str, db: Session = Depends(get_db)):
    parsed = _valid_map_id(map_id)
    if not parsed:
        raise HTTPException(400, detail=tr(db, "invalid_map_id"))
    try:
        payload = await caltopo_client(db).get_map(parsed, 0)
        state = normalize_state(payload)
        return {"ok": True, "map_id": parsed, "source": "live", "state": state}
    except Exception as exc:
        # Watched maps can still be previewed from the last locally known state if CalTopo is temporarily unavailable.
        watch = db.scalar(select(MapWatch).where(MapWatch.map_id == parsed))
        if watch:
            state = current_state(db, parsed)
            if state.get("features"):
                return {"ok": True, "map_id": parsed, "source": "local", "warning": str(exc), "state": state}
        raise HTTPException(502, detail=tr(db, "preview_failed", error=friendly_error(db, exc)))


@app.post("/maps/picker", dependencies=[Depends(require_roles("admin", "user"))])
async def save_picked_maps(request: Request, map_ids: list[str] = Form(default=[]), db: Session = Depends(get_db)):
    team_id = configured_team_id(db)
    if not team_id:
        flash_t(request, db, "team_id_not_configured", "danger")
        return RedirectResponse("/maps/picker", status_code=303)
    try:
        catalog = await refresh_team_catalog(db, team_id)
    except Exception as exc:
        flash_t(request, db, "map_list_failed", "danger", error=friendly_error(db, exc))
        return RedirectResponse("/maps/picker", status_code=303)

    by_id = {item["id"]: item for item in catalog}
    catalog_ids = set(by_id)
    selected = {map_id for map_id in map_ids if map_id in catalog_ids}
    existing = {row.map_id: row for row in db.scalars(select(MapWatch)).all()}

    added = 0
    removed = 0
    for map_id in selected:
        before = existing.get(map_id)
        # Preserve a manually paused existing watch. Selecting it means "keep monitored", not "reactivate".
        await ensure_watch(db, map_id, source="picker", title=by_id[map_id]["title"], reactivate=(before is None))
        if before is None:
            added += 1

    # Unchecking a visible team map removes only its watch registration; retained history is untouched.
    for map_id in catalog_ids - selected:
        watch = existing.get(map_id)
        if watch is None:
            continue
        db.delete(watch)
        add_audit(
            db, "watch_removed", map_id=map_id,
            detail="removed via map picker; stored history retained",
            actor_username=request.state.user.username, actor_role=request.state.user.role, client_ip=client_ip(request),
        )
        removed += 1

    db.commit()
    flash_t(request, db, "picker_saved", "success", added=added, removed=removed)
    return RedirectResponse("/maps/picker", status_code=303)


@app.post("/maps/{map_id}/toggle", dependencies=[Depends(require_roles("admin"))])
def toggle_map(request: Request, map_id: str, db: Session = Depends(get_db)):
    watch = db.scalar(select(MapWatch).where(MapWatch.map_id == map_id))
    if not watch:
        raise HTTPException(404)
    watch.active = not watch.active
    if watch.active:
        watch.auto_pause_at = utcnow() + timedelta(days=AUTO_PAUSE_DAYS)
    add_audit(
        db, "watch_toggle", map_id=map_id, detail=f"active={watch.active}",
        actor_username=request.state.user.username, actor_role=request.state.user.role, client_ip=client_ip(request),
    )
    db.commit()
    flash_t(request, db, "backup_activated" if watch.active else "backup_paused", "success")
    return RedirectResponse(f"/maps/{map_id}", status_code=303)


@app.post("/maps/{map_id}/delete", dependencies=[Depends(require_roles("admin"))])
def delete_map_watch(request: Request, map_id: str, db: Session = Depends(get_db)):
    watch = db.scalar(select(MapWatch).where(MapWatch.map_id == map_id))
    if not watch:
        raise HTTPException(404)
    title = watch.title or watch.map_id
    source = watch.source
    db.delete(watch)
    add_audit(
        db, "watch_removed", map_id=map_id,
        detail=f"title={title!r}, source={source}; stored history retained",
        actor_username=request.state.user.username, actor_role=request.state.user.role, client_ip=client_ip(request),
    )
    db.commit()
    suffix = tr(db, "watch_history_retained")
    if source == "pattern":
        suffix += tr(db, "watch_pattern_warning")
    flash_t(request, db, "watch_removed", "success", title=title, suffix=suffix)
    return RedirectResponse("/", status_code=303)


@app.post("/maps/{map_id}/backup", dependencies=[Depends(require_roles("admin", "user"))])
async def backup_now(request: Request, map_id: str, db: Session = Depends(get_db)):
    watch = db.scalar(select(MapWatch).where(MapWatch.map_id == map_id))
    if not watch:
        raise HTTPException(404)
    try:
        snap = await backup_watch(db, watch, force_full=True, reason="manual")
        if snap is None:
            flash_t(request, db, "no_changes_no_snapshot", "info")
        else:
            flash_t(request, db, "snapshot_created", "success", id=snap.id)
    except Exception as exc:
        flash_t(request, db, "backup_failed", "danger", error=friendly_error(db, exc))
    return RedirectResponse(f"/maps/{map_id}", status_code=303)


@app.post("/maps/{map_id}/interval", dependencies=[Depends(require_roles("admin"))])
def set_map_interval(request: Request, map_id: str, interval_minutes: str = Form(""), db: Session = Depends(get_db)):
    watch = db.scalar(select(MapWatch).where(MapWatch.map_id == map_id))
    if not watch:
        raise HTTPException(404)
    raw = interval_minutes.strip()
    if not raw or raw == "0":
        watch.poll_interval_seconds = None
        detail = "inherit-global"
    else:
        try:
            minutes = int(raw)
        except ValueError:
            minutes = 0
        if minutes < 1 or minutes > 10080:
            flash_t(request, db, "interval_invalid", "danger")
            return RedirectResponse(f"/maps/{map_id}", status_code=303)
        watch.poll_interval_seconds = minutes * 60
        detail = f"{minutes}m"
    add_audit(
        db, "watch_interval_changed", map_id=map_id, detail=detail,
        actor_username=request.state.user.username, actor_role=request.state.user.role, client_ip=client_ip(request),
    )
    db.commit()
    flash_t(request, db, "interval_saved", "success")
    return RedirectResponse(f"/maps/{map_id}", status_code=303)


@app.post("/maps/{map_id}/title", dependencies=[Depends(require_roles("admin"))])
def set_map_title(request: Request, map_id: str, title: str = Form(...), db: Session = Depends(get_db)):
    watch = db.scalar(select(MapWatch).where(MapWatch.map_id == map_id))
    if not watch:
        raise HTTPException(404)
    watch.title = title.strip()[:300]
    db.commit()
    flash_t(request, db, "display_name_saved", "success")
    return RedirectResponse(f"/maps/{map_id}", status_code=303)


@app.get("/maps/{map_id}", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
def map_detail(request: Request, map_id: str, db: Session = Depends(get_db)):
    watch = db.scalar(select(MapWatch).where(MapWatch.map_id == map_id))
    if not watch:
        raise HTTPException(404)
    snaps = db.scalars(select(Snapshot).where(Snapshot.map_id == map_id).order_by(desc(Snapshot.captured_at)).limit(200)).all()
    for snap in snaps:
        snap.storage_bytes = len(snap.state_gz or b"")
    objects = object_overview(db, map_id)
    effective_interval = effective_poll_interval_seconds(db, watch)
    global_interval = global_poll_interval_seconds(db)
    map_storage_info = map_storage(db, map_id)
    return templates.TemplateResponse(
        request, "map.html", ctx(
            request, watch=watch, snaps=snaps, objects=objects, map_storage=map_storage_info,
            effective_interval_seconds=effective_interval,
            global_interval_seconds=global_interval,
        )
    )


@app.get("/maps/{map_id}/compare", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
def compare_snapshots(
    request: Request,
    map_id: str,
    snapshot_a: int = Query(...),
    snapshot_b: int = Query(...),
    db: Session = Depends(get_db),
):
    watch = db.scalar(select(MapWatch).where(MapWatch.map_id == map_id))
    if not watch:
        raise HTTPException(404)
    left = db.get(Snapshot, snapshot_a)
    right = db.get(Snapshot, snapshot_b)
    if not left or not right or left.map_id != map_id or right.map_id != map_id:
        raise HTTPException(404, detail=tr(db, "snapshots_wrong_map"))
    diff = compare_states(snapshot_state(left), snapshot_state(right))
    counts = {key: 0 for key in ("added", "removed", "changed")}
    for item in diff:
        counts[item.status] = counts.get(item.status, 0) + 1
    return templates.TemplateResponse(
        request, "compare.html", ctx(request, watch=watch, left=left, right=right, diff=diff, counts=counts)
    )


@app.get("/maps/{map_id}/objects/{object_id}", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
def object_history(request: Request, map_id: str, object_id: str, db: Session = Depends(get_db)):
    versions = db.scalars(
        select(ObjectVersion).where(and_(ObjectVersion.map_id == map_id, ObjectVersion.object_id == object_id))
        .order_by(desc(ObjectVersion.captured_at))
    ).all()
    if not versions:
        raise HTTPException(404)
    for version in versions:
        version.feature = unpack_json(version.feature_gz) if version.feature_gz else None
    return templates.TemplateResponse(request, "object.html", ctx(request, map_id=map_id, object_id=object_id, versions=versions))


@app.post("/versions/{version_id}/restore", dependencies=[Depends(require_auth)])
async def restore_version(request: Request, version_id: int, db: Session = Depends(get_db)):
    version = db.get(ObjectVersion, version_id)
    if not version or version.deleted or not version.feature_gz:
        raise HTTPException(404)
    user = request.state.user
    ip = client_ip(request)
    try:
        action = await restore_one_version(
            db, version.map_id, unpack_json(version.feature_gz),
            actor_username=user.username, actor_role=user.role, client_ip=ip, source_version_id=version.id,
        )
        flash_t(request, db, "object_restore_result", "success", action=(tr(db, "edited") if action == "edited" else tr(db, "recreated") if action == "re-created" else action))
    except Exception as exc:
        add_audit(
            db, "restore_object_failed", map_id=version.map_id, object_id=version.object_id, object_title=version.title or None,
            detail=f"version={version.id}, error={str(exc)[:1800]}",
            actor_username=user.username, actor_role=user.role, client_ip=ip,
        )
        db.commit()
        flash_t(request, db, "restore_failed", "danger", error=friendly_error(db, exc))
    return RedirectResponse(f"/maps/{version.map_id}/objects/{quote(version.object_id)}", status_code=303)


@app.get("/snapshots/{snapshot_id}", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
def snapshot_detail(request: Request, snapshot_id: int, db: Session = Depends(get_db)):
    snap = db.get(Snapshot, snapshot_id)
    if not snap:
        raise HTTPException(404)
    snap.storage_bytes = len(snap.state_gz or b"")
    target = snapshot_state(snap)
    live_local = current_state(db, snap.map_id)
    diff = diff_states(target, live_local)
    return templates.TemplateResponse(request, "snapshot.html", ctx(request, snap=snap, diff=diff, state=target))


@app.get("/snapshots/{snapshot_id}/geojson", dependencies=[Depends(require_auth)])
def snapshot_geojson(snapshot_id: int, db: Session = Depends(get_db)):
    snap = db.get(Snapshot, snapshot_id)
    if not snap:
        raise HTTPException(404)
    return Response(json.dumps(snapshot_state(snap), ensure_ascii=False), media_type="application/geo+json")


@app.post("/snapshots/{snapshot_id}/restore", dependencies=[Depends(require_auth)])
async def restore_snapshot_route(request: Request, snapshot_id: int, confirmation: str = Form(...), db: Session = Depends(get_db)):
    snap = db.get(Snapshot, snapshot_id)
    if not snap:
        raise HTTPException(404)
    required = f"RESTORE {snap.map_id}"
    if confirmation.strip() != required:
        flash_t(request, db, "confirmation_mismatch", "danger", expected=required)
        return RedirectResponse(f"/snapshots/{snapshot_id}", status_code=303)
    user = request.state.user
    ip = client_ip(request)
    try:
        stats = await restore_snapshot(db, snap, actor_username=user.username, actor_role=user.role, client_ip=ip)
        flash_t(
            request, db, "rollback_done", "success" if not stats["errors"] else "warning",
            stats=", ".join([
                f"{tr(db, 'changed')}: {stats.get('changed', 0)}",
                f"{tr(db, 'restored')}: {stats.get('restored', 0)}",
                f"{tr(db, 'removed')}: {stats.get('removed', 0)}",
                f"{tr(db, 'skipped')}: {stats.get('skipped', 0)}",
                f"{tr(db, 'errors')}: {stats.get('errors', 0)}",
            ]),
        )
    except Exception as exc:
        add_audit(
            db, "restore_snapshot_failed", map_id=snap.map_id, object_title="Gesamte Karte",
            detail=f"snapshot={snap.id}, error={str(exc)[:1800]}",
            actor_username=user.username, actor_role=user.role, client_ip=ip,
        )
        db.commit()
        flash_t(request, db, "rollback_failed", "danger", error=friendly_error(db, exc))
    return RedirectResponse(f"/snapshots/{snapshot_id}", status_code=303)


@app.post("/rules", dependencies=[Depends(require_roles("admin"))])
async def add_rule(request: Request, team_id: str = Form(...), pattern: str = Form(...), db: Session = Depends(get_db)):
    team_id, pattern = team_id.strip(), pattern.strip()
    try:
        re.compile(pattern)
    except re.error as exc:
        flash_t(request, db, "regex_invalid", "danger", error=friendly_error(db, exc))
        return RedirectResponse("/", status_code=303)
    rule = TeamRule(team_id=team_id, pattern=pattern)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    try:
        matches = await discover_rule(db, rule)
        flash_t(request, db, "rule_saved_matches", "success", count=matches)
    except Exception as exc:
        flash_t(request, db, "rule_saved_scan_failed", "danger", error=friendly_error(db, exc))
    return RedirectResponse("/", status_code=303)


@app.post("/rules/{rule_id}/scan", dependencies=[Depends(require_roles("admin"))])
async def scan_rule(request: Request, rule_id: int, db: Session = Depends(get_db)):
    rule = db.get(TeamRule, rule_id)
    if not rule:
        raise HTTPException(404)
    try:
        matches = await discover_rule(db, rule)
        flash_t(request, db, "matches_found", "success", count=matches)
    except Exception as exc:
        flash_t(request, db, "scan_failed", "danger", error=friendly_error(db, exc))
    return RedirectResponse("/", status_code=303)


@app.post("/rules/{rule_id}/toggle", dependencies=[Depends(require_roles("admin"))])
def toggle_rule(request: Request, rule_id: int, db: Session = Depends(get_db)):
    rule = db.get(TeamRule, rule_id)
    if not rule:
        raise HTTPException(404)
    rule.active = not rule.active
    db.commit()
    flash_t(request, db, "rule_activated" if rule.active else "rule_paused", "success")
    return RedirectResponse("/", status_code=303)


@app.get("/settings", response_class=HTMLResponse, dependencies=[Depends(require_roles("admin"))])
def settings_page(request: Request, db: Session = Depends(get_db)):
    try:
        credential_secret_configured = bool(effective_credential_secret(db))
        credential_secret_error = None
    except ValueError as exc:
        credential_secret_configured = False
        credential_secret_error = str(exc)
    app_secret_source = "file" if settings.app_secret_key_file and not os.getenv("APP_SECRET_KEY") else "environment"
    return templates.TemplateResponse(
        request, "settings.html", ctx(
            request,
            global_interval_minutes=global_poll_interval_seconds(db) // 60,
            team_id=configured_team_id(db),
            disk_warning_mb=disk_warning_free_mb(db),
            disk_hard_mb=disk_hard_free_mb(db),
            disk=current_disk_status(db),
            ui_language=current_ui_language(db),
            credential_id=effective_credential_id(db),
            credential_id_source=credential_id_source(db),
            credential_secret_configured=credential_secret_configured,
            credential_secret_source=credential_secret_source(db),
            credential_secret_error=credential_secret_error,
            caltopo_base_url=effective_caltopo_base_url(db),
            discovery_interval=discovery_interval_seconds(db),
            full_verify_every_value=full_verify_every(db),
            app_secret_configured=settings.app_secret_key not in {"", "change-me-to-a-long-random-string"},
            app_secret_source=app_secret_source,
            cookie_secure=settings.cookie_secure,
            timezone=settings.timezone,
        )
    )


@app.post("/settings", dependencies=[Depends(require_roles("admin"))])
async def save_settings(
    request: Request,
    global_interval_minutes: int = Form(...),
    team_id: str = Form(""),
    disk_warning_mb: int = Form(4096),
    disk_hard_mb: int = Form(2048),
    ui_language: str = Form(DEFAULT_LANGUAGE),
    credential_id: str = Form(""),
    credential_secret: str = Form(""),
    clear_credential_secret: str | None = Form(None),
    caltopo_base_url: str = Form("https://caltopo.com"),
    discovery_interval: int = Form(300),
    full_verify_every_value: int = Form(30),
    db: Session = Depends(get_db),
):
    if global_interval_minutes < 1 or global_interval_minutes > 10080:
        flash_t(request, db, "global_interval_invalid", "danger")
        return RedirectResponse("/settings", status_code=303)
    team_id = team_id.strip()
    if team_id and not re.fullmatch(r"[A-Za-z0-9_-]{3,32}", team_id):
        flash_t(request, db, "invalid_team_id", "danger")
        return RedirectResponse("/settings", status_code=303)
    if disk_hard_mb < 256 or disk_warning_mb < disk_hard_mb:
        flash_t(request, db, "invalid_storage_limits", "danger")
        return RedirectResponse("/settings", status_code=303)
    credential_id = credential_id.strip()
    if credential_id and not re.fullmatch(r"[A-Za-z0-9_-]{3,64}", credential_id):
        flash_t(request, db, "invalid_credential_id", "danger")
        return RedirectResponse("/settings", status_code=303)
    caltopo_base_url = caltopo_base_url.strip().rstrip("/")
    if not re.fullmatch(r"https://[^\s/]+(?:/[^\s]*)?", caltopo_base_url):
        flash_t(request, db, "invalid_caltopo_url", "danger")
        return RedirectResponse("/settings", status_code=303)
    if discovery_interval < 60 or discovery_interval > 86400:
        flash_t(request, db, "invalid_discovery_interval", "danger")
        return RedirectResponse("/settings", status_code=303)
    if full_verify_every_value < 1 or full_verify_every_value > 10000:
        flash_t(request, db, "invalid_full_verify", "danger")
        return RedirectResponse("/settings", status_code=303)

    ui_language = normalize_language(ui_language)
    set_app_setting(db, GLOBAL_POLL_KEY, str(global_interval_minutes * 60))
    set_app_setting(db, TEAM_ID_KEY, team_id)
    set_app_setting(db, DISK_WARNING_MB_KEY, str(disk_warning_mb))
    set_app_setting(db, DISK_HARD_MB_KEY, str(disk_hard_mb))
    set_app_setting(db, UI_LANGUAGE_KEY, ui_language)
    set_app_setting(db, CALTOPO_CREDENTIAL_ID_KEY, credential_id)
    set_app_setting(db, CALTOPO_BASE_URL_KEY, caltopo_base_url)
    set_app_setting(db, DISCOVERY_INTERVAL_SECONDS_KEY, str(discovery_interval))
    set_app_setting(db, FULL_VERIFY_EVERY_KEY, str(full_verify_every_value))
    if clear_credential_secret:
        clear_credential_secret_override(db)
    elif credential_secret.strip():
        set_credential_secret(db, credential_secret)

    add_audit(
        db,
        "settings_changed",
        detail=(
            f"global_interval={global_interval_minutes}m, team_id={team_id}, "
            f"credential_id={'configured' if credential_id else 'empty'}, "
            f"credential_secret={'updated' if credential_secret.strip() else ('environment' if clear_credential_secret else 'unchanged')}, "
            f"caltopo_base_url={caltopo_base_url}, discovery_interval={discovery_interval}s, "
            f"full_verify_every={full_verify_every_value}, disk_warning_mb={disk_warning_mb}, "
            f"disk_hard_mb={disk_hard_mb}, ui_language={ui_language}"
        ),
        actor_username=request.state.user.username, actor_role=request.state.user.role, client_ip=client_ip(request),
    )
    db.commit()

    if team_id and effective_credential_id(db):
        try:
            maps = await refresh_team_catalog(db, team_id)
            flash_t(request, db, "settings_saved_catalog", "success", count=len(maps))
        except Exception as exc:
            flash_t(request, db, "settings_saved_catalog_failed", "warning", error=friendly_error(db, exc))
    else:
        flash_t(request, db, "settings_saved", "success")
    return RedirectResponse("/settings", status_code=303)


@app.get("/settings/maintenance", response_class=HTMLResponse, dependencies=[Depends(require_roles("admin"))])
def maintenance_page(request: Request, db: Session = Depends(get_db)):
    storage = storage_overview(db)
    disk = current_disk_status(db)
    return templates.TemplateResponse(request, "maintenance.html", ctx(request, storage=storage, disk=disk))


@app.post("/settings/maintenance/snapshots", dependencies=[Depends(require_roles("admin"))])
def maintenance_prune_snapshots(
    request: Request,
    map_id: str = Form(""),
    older_than_days: int = Form(...),
    keep_latest: int = Form(3),
    confirmation: str = Form(""),
    db: Session = Depends(get_db),
):
    if confirmation.strip() != "DELETE SNAPSHOTS":
        flash_t(request, db, "confirm_delete_snapshots", "danger")
        return RedirectResponse("/settings/maintenance", status_code=303)
    try:
        count = prune_snapshots(db, map_id=map_id.strip() or None, older_than_days=older_than_days, keep_latest=keep_latest)
    except ValueError as exc:
        flash_t(request, db, "maintenance_failed", "danger", error=exc)
        return RedirectResponse("/settings/maintenance", status_code=303)
    add_audit(
        db, "maintenance_snapshots_pruned", map_id=map_id.strip() or None,
        detail=f"deleted={count}, older_than_days={older_than_days}, keep_latest={keep_latest}",
        actor_username=request.state.user.username, actor_role=request.state.user.role, client_ip=client_ip(request),
    )
    db.commit()
    flash_t(request, db, "snapshots_deleted", "success", count=count)
    return RedirectResponse("/settings/maintenance", status_code=303)


@app.post("/settings/maintenance/object-history", dependencies=[Depends(require_roles("admin"))])
def maintenance_prune_object_history(
    request: Request,
    map_id: str = Form(""),
    older_than_days: int = Form(...),
    confirmation: str = Form(""),
    db: Session = Depends(get_db),
):
    if confirmation.strip() != "DELETE HISTORY":
        flash_t(request, db, "confirm_delete_history", "danger")
        return RedirectResponse("/settings/maintenance", status_code=303)
    try:
        count = prune_object_versions(db, map_id=map_id.strip() or None, older_than_days=older_than_days)
    except ValueError as exc:
        flash_t(request, db, "maintenance_failed", "danger", error=exc)
        return RedirectResponse("/settings/maintenance", status_code=303)
    add_audit(
        db, "maintenance_object_history_pruned", map_id=map_id.strip() or None,
        detail=f"deleted={count}, older_than_days={older_than_days}; latest version per object retained",
        actor_username=request.state.user.username, actor_role=request.state.user.role, client_ip=client_ip(request),
    )
    db.commit()
    flash_t(request, db, "history_deleted", "success", count=count)
    return RedirectResponse("/settings/maintenance", status_code=303)


@app.post("/settings/maintenance/archive/{map_id}/purge", dependencies=[Depends(require_roles("admin"))])
def maintenance_purge_archived_map(
    request: Request, map_id: str, confirmation: str = Form(""), db: Session = Depends(get_db)
):
    if confirmation.strip() != map_id:
        flash_t(request, db, "purge_enter_map_id", "danger", map_id=map_id)
        return RedirectResponse("/settings/maintenance", status_code=303)
    try:
        counts = purge_archived_map(db, map_id)
    except ValueError as exc:
        flash_t(request, db, "archive_delete_failed", "danger", error=friendly_error(db, exc))
        return RedirectResponse("/settings/maintenance", status_code=303)
    add_audit(
        db, "maintenance_archived_map_purged", map_id=map_id, detail=json.dumps(counts, sort_keys=True),
        actor_username=request.state.user.username, actor_role=request.state.user.role, client_ip=client_ip(request),
    )
    db.commit()
    flash_t(request, db, "archive_deleted", "success", map_id=map_id, counts=counts)
    return RedirectResponse("/settings/maintenance", status_code=303)




@app.post("/settings/maintenance/db-backup/delete", dependencies=[Depends(require_roles("admin"))])
def maintenance_delete_db_backup(
    request: Request, filename: str = Form(...), confirmation: str = Form(""), db: Session = Depends(get_db)
):
    if confirmation.strip() != filename:
        flash_t(request, db, "db_backup_enter_filename", "danger")
        return RedirectResponse("/settings/maintenance", status_code=303)
    try:
        size = delete_database_backup(filename)
    except ValueError as exc:
        flash_t(request, db, "db_backup_delete_failed", "danger", error=friendly_error(db, exc))
        return RedirectResponse("/settings/maintenance", status_code=303)
    add_audit(
        db, "maintenance_db_backup_deleted", detail=f"filename={filename}, bytes={size}",
        actor_username=request.state.user.username, actor_role=request.state.user.role, client_ip=client_ip(request),
    )
    db.commit()
    flash_t(request, db, "db_backup_deleted", "success", filename=filename, size=human_bytes(size))
    return RedirectResponse("/settings/maintenance", status_code=303)


@app.post("/settings/maintenance/vacuum", dependencies=[Depends(require_roles("admin"))])
def maintenance_vacuum(request: Request, confirmation: str = Form(""), db: Session = Depends(get_db)):
    if confirmation.strip() != "VACUUM":
        flash_t(request, db, "confirm_vacuum", "danger")
        return RedirectResponse("/settings/maintenance", status_code=303)
    before = storage_overview(db).database_bytes
    disk = current_disk_status(db)
    # SQLite VACUUM rewrites the database and can temporarily require roughly another database-sized file.
    if disk.free_bytes - before <= disk.hard_free_bytes:
        flash_t(
            request, db, "vacuum_safety_abort", "danger",
            free=human_bytes(disk.free_bytes), db=human_bytes(before), reserve=human_bytes(disk.hard_free_bytes),
        )
        return RedirectResponse("/settings/maintenance", status_code=303)
    actor_username = request.state.user.username
    actor_role = request.state.user.role
    actor_ip = client_ip(request)
    db.close()
    try:
        vacuum_database()
    except Exception as exc:
        flash_t(request, db, "vacuum_failed", "danger", error=friendly_error(db, exc))
        return RedirectResponse("/settings/maintenance", status_code=303)
    with SessionLocal() as audit_db:
        after = storage_overview(audit_db).database_bytes
        add_audit(
            audit_db, "maintenance_vacuum", detail=f"before={before}, after={after}",
            actor_username=actor_username, actor_role=actor_role, client_ip=actor_ip,
        )
        audit_db.commit()
    flash_t(request, db, "vacuum_done", "success", before=human_bytes(before), after=human_bytes(after))
    return RedirectResponse("/settings/maintenance", status_code=303)


@app.get("/users", response_class=HTMLResponse, dependencies=[Depends(require_roles("admin"))])
def users_page(request: Request, db: Session = Depends(get_db)):
    users = db.scalars(select(AppUser).order_by(AppUser.username)).all()
    return templates.TemplateResponse(request, "users.html", ctx(request, users=users))


@app.post("/users", dependencies=[Depends(require_roles("admin"))])
def add_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
):
    username = username.strip()
    role = role.strip().lower()
    if not re.fullmatch(r"[A-Za-z0-9._@+-]{3,120}", username):
        flash_t(request, db, "invalid_username", "danger")
        return RedirectResponse("/users", status_code=303)
    if role not in ROLES:
        flash_t(request, db, "invalid_role", "danger")
        return RedirectResponse("/users", status_code=303)
    if len(password) < 12:
        flash_t(request, db, "password_min", "danger")
        return RedirectResponse("/users", status_code=303)
    if db.scalar(select(AppUser).where(AppUser.username == username)):
        flash_t(request, db, "username_exists", "danger")
        return RedirectResponse("/users", status_code=303)
    db.add(AppUser(username=username, password_hash=hash_password(password), role=role, active=True))
    add_audit(
        db, "user_created", detail=f"username={username}, role={role}",
        actor_username=request.state.user.username, actor_role=request.state.user.role, client_ip=client_ip(request),
    )
    db.commit()
    flash_t(request, db, "user_created", "success", username=username, role=role)
    return RedirectResponse("/users", status_code=303)


@app.post("/users/{user_id}/role", dependencies=[Depends(require_roles("admin"))])
def change_user_role(request: Request, user_id: int, role: str = Form(...), db: Session = Depends(get_db)):
    target = db.get(AppUser, user_id)
    if not target:
        raise HTTPException(404)
    role = role.strip().lower()
    if role not in ROLES:
        flash_t(request, db, "invalid_role", "danger")
        return RedirectResponse("/users", status_code=303)
    if target.username.lower() == "admin":
        flash_t(request, db, "admin_role_protected", "danger")
        return RedirectResponse("/users", status_code=303)
    if _last_admin_guard(db, target, new_role=role):
        flash_t(request, db, "last_admin_demote", "danger")
        return RedirectResponse("/users", status_code=303)
    old_role = target.role
    target.role = role
    add_audit(
        db, "user_role_changed", detail=f"username={target.username}, {old_role}->{role}",
        actor_username=request.state.user.username, actor_role=request.state.user.role, client_ip=client_ip(request),
    )
    db.commit()
    flash_t(request, db, "role_changed", "success", username=target.username)
    return RedirectResponse("/users", status_code=303)


@app.post("/users/{user_id}/password", dependencies=[Depends(require_roles("admin"))])
def reset_user_password(request: Request, user_id: int, password: str = Form(...), db: Session = Depends(get_db)):
    target = db.get(AppUser, user_id)
    if not target:
        raise HTTPException(404)
    if target.username.lower() == "admin" and target.id != request.state.user.id:
        flash_t(request, db, "admin_password_self_only", "danger")
        return RedirectResponse("/users", status_code=303)
    if len(password) < 12:
        flash_t(request, db, "password_min", "danger")
        return RedirectResponse("/users", status_code=303)
    target.password_hash = hash_password(password)
    add_audit(
        db, "user_password_reset", detail=f"username={target.username}",
        actor_username=request.state.user.username, actor_role=request.state.user.role, client_ip=client_ip(request),
    )
    db.commit()
    flash_t(request, db, "password_reset", "success", username=target.username)
    return RedirectResponse("/users", status_code=303)


@app.post("/users/{user_id}/toggle", dependencies=[Depends(require_roles("admin"))])
def toggle_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    target = db.get(AppUser, user_id)
    if not target:
        raise HTTPException(404)
    if target.username.lower() == "admin":
        flash_t(request, db, "admin_disable_protected", "danger")
        return RedirectResponse("/users", status_code=303)
    if target.id == request.state.user.id:
        flash_t(request, db, "self_disable", "danger")
        return RedirectResponse("/users", status_code=303)
    new_active = not target.active
    if _last_admin_guard(db, target, new_active=new_active):
        flash_t(request, db, "last_admin_disable", "danger")
        return RedirectResponse("/users", status_code=303)
    target.active = new_active
    add_audit(
        db, "user_toggle", detail=f"username={target.username}, active={target.active}",
        actor_username=request.state.user.username, actor_role=request.state.user.role, client_ip=client_ip(request),
    )
    db.commit()
    flash_t(request, db, "user_activated" if target.active else "user_deactivated", "success", username=target.username)
    return RedirectResponse("/users", status_code=303)


@app.post("/users/{user_id}/delete", dependencies=[Depends(require_roles("admin"))])
def delete_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    target = db.get(AppUser, user_id)
    if not target:
        raise HTTPException(404)
    if target.username.lower() == "admin":
        flash_t(request, db, "admin_delete_protected", "danger")
        return RedirectResponse("/users", status_code=303)
    if target.id == request.state.user.id:
        flash_t(request, db, "self_delete", "danger")
        return RedirectResponse("/users", status_code=303)
    if _last_admin_guard(db, target, new_active=False):
        flash_t(request, db, "last_admin_delete", "danger")
        return RedirectResponse("/users", status_code=303)
    username = target.username
    db.delete(target)
    add_audit(
        db, "user_deleted", detail=f"username={username}",
        actor_username=request.state.user.username, actor_role=request.state.user.role, client_ip=client_ip(request),
    )
    db.commit()
    flash_t(request, db, "user_deleted", "success", username=username)
    return RedirectResponse("/users", status_code=303)


@app.get("/audit", response_class=HTMLResponse, dependencies=[Depends(require_roles("admin"))])
def restore_audit(request: Request, db: Session = Depends(get_db)):
    audits = db.scalars(
        select(AuditLog).where(AuditLog.action.like("restore%"))
        .order_by(desc(AuditLog.created_at)).limit(1000)
    ).all()
    return templates.TemplateResponse(request, "audit.html", ctx(request, audits=audits))
