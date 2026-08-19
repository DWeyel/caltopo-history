# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .caltopo import CalTopoClient
from .config import settings
from .db import AppSetting, AuditLog, MapWatch, Snapshot, TeamRule, utcnow
from .storage_guard import DiskSpaceBlocked, disk_space_status
from .secret_store import decrypt_secret, encrypt_secret
from .history import (
    create_snapshot,
    create_snapshot_if_changed,
    diff_states,
    feature_type,
    feature_title,
    ingest_full,
    ingest_incremental,
    map_title,
    response_timestamp,
    snapshot_state,
)


SUPPORTED_WRITE_TYPES = {"Marker", "Shape"}
GLOBAL_POLL_KEY = "global_poll_interval_seconds"
TEAM_ID_KEY = "caltopo_team_id"
AUTO_PAUSE_DAYS = 7
QUIET_SNAPSHOT_MINUTES = 30
DISK_WARNING_MB_KEY = "disk_warning_free_mb"
DISK_HARD_MB_KEY = "disk_hard_free_mb"
UI_LANGUAGE_KEY = "ui_language"
CALTOPO_CREDENTIAL_ID_KEY = "caltopo_credential_id"
CALTOPO_CREDENTIAL_SECRET_KEY = "caltopo_credential_secret"
CALTOPO_BASE_URL_KEY = "caltopo_base_url"
DISCOVERY_INTERVAL_SECONDS_KEY = "discovery_interval_seconds"
FULL_VERIFY_EVERY_KEY = "full_verify_every"
COOKIE_SECURE_KEY = "cookie_secure"
DEFAULT_DISK_WARNING_MB = 4096
DEFAULT_DISK_HARD_MB = 2048


def _aware(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def add_audit(
    db: Session,
    action: str,
    *,
    map_id: str | None = None,
    object_id: str | None = None,
    detail: str = "",
    actor_username: str | None = None,
    actor_role: str | None = None,
    client_ip: str | None = None,
    object_title: str | None = None,
) -> None:
    db.add(AuditLog(
        action=action,
        map_id=map_id,
        object_id=object_id,
        detail=detail,
        actor_username=actor_username,
        actor_role=actor_role,
        client_ip=client_ip,
        object_title=object_title,
    ))


def get_app_setting(db: Session, key: str, default: str = "") -> str:
    row = db.get(AppSetting, key)
    return row.value if row is not None else default


def set_app_setting(db: Session, key: str, value: str) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value


def clear_app_setting(db: Session, key: str) -> None:
    row = db.get(AppSetting, key)
    if row is not None:
        db.delete(row)


def effective_credential_id(db: Session) -> str:
    row = db.get(AppSetting, CALTOPO_CREDENTIAL_ID_KEY)
    if row is not None:
        return row.value.strip()
    return settings.credential_id.strip()


def credential_id_source(db: Session) -> str:
    return "settings" if db.get(AppSetting, CALTOPO_CREDENTIAL_ID_KEY) is not None else "environment"


def effective_credential_secret(db: Session) -> str:
    row = db.get(AppSetting, CALTOPO_CREDENTIAL_SECRET_KEY)
    if row is not None:
        return decrypt_secret(row.value)
    return settings.credential_secret.strip()


def credential_secret_source(db: Session) -> str:
    return "settings" if db.get(AppSetting, CALTOPO_CREDENTIAL_SECRET_KEY) is not None else "environment"


def set_credential_secret(db: Session, value: str) -> None:
    set_app_setting(db, CALTOPO_CREDENTIAL_SECRET_KEY, encrypt_secret(value.strip()))


def clear_credential_secret_override(db: Session) -> None:
    row = db.get(AppSetting, CALTOPO_CREDENTIAL_SECRET_KEY)
    if row is not None:
        db.delete(row)


def effective_caltopo_base_url(db: Session) -> str:
    return get_app_setting(db, CALTOPO_BASE_URL_KEY, settings.caltopo_base_url).strip().rstrip("/")


def discovery_interval_seconds(db: Session) -> int:
    try:
        return max(60, int(get_app_setting(db, DISCOVERY_INTERVAL_SECONDS_KEY, str(settings.discovery_interval_seconds))))
    except (TypeError, ValueError):
        return max(60, settings.discovery_interval_seconds)


def full_verify_every(db: Session) -> int:
    try:
        return max(1, int(get_app_setting(db, FULL_VERIFY_EVERY_KEY, str(settings.full_verify_every))))
    except (TypeError, ValueError):
        return max(1, settings.full_verify_every)


def effective_cookie_secure(db: Session) -> bool:
    row = db.get(AppSetting, COOKIE_SECURE_KEY)
    if row is None:
        return settings.cookie_secure
    raw = row.value.strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return settings.cookie_secure


def cookie_secure_source(db: Session) -> str:
    return "settings" if db.get(AppSetting, COOKIE_SECURE_KEY) is not None else "environment"


def caltopo_client(db: Session) -> CalTopoClient:
    return CalTopoClient(
        credential_id=effective_credential_id(db),
        credential_secret=effective_credential_secret(db),
        base_url=effective_caltopo_base_url(db),
    )


def global_poll_interval_seconds(db: Session) -> int:
    raw = get_app_setting(db, GLOBAL_POLL_KEY, str(settings.poll_interval_seconds))
    try:
        return max(60, int(raw))
    except (TypeError, ValueError):
        return max(60, settings.poll_interval_seconds)


def effective_poll_interval_seconds(db: Session, watch: MapWatch) -> int:
    return max(60, watch.poll_interval_seconds or global_poll_interval_seconds(db))


def configured_team_id(db: Session) -> str:
    return get_app_setting(db, TEAM_ID_KEY, "").strip()


def disk_warning_free_mb(db: Session) -> int:
    try:
        return max(0, int(get_app_setting(db, DISK_WARNING_MB_KEY, str(DEFAULT_DISK_WARNING_MB))))
    except (TypeError, ValueError):
        return DEFAULT_DISK_WARNING_MB


def disk_hard_free_mb(db: Session) -> int:
    try:
        return max(0, int(get_app_setting(db, DISK_HARD_MB_KEY, str(DEFAULT_DISK_HARD_MB))))
    except (TypeError, ValueError):
        return DEFAULT_DISK_HARD_MB


def current_disk_status(db: Session):
    return disk_space_status(
        warning_free_mb=disk_warning_free_mb(db),
        hard_free_mb=disk_hard_free_mb(db),
    )


def ensure_backup_disk_space(db: Session) -> None:
    status = current_disk_status(db)
    if status.hard_blocked:
        raise DiskSpaceBlocked(status.free_bytes, status.hard_free_bytes)


def _account_display_name(account: dict[str, Any] | None, account_id: str) -> str:
    props = (account or {}).get("properties") or {}
    for key in ("title", "alias"):
        value = str(props.get(key) or "").strip()
        if value:
            return value
    person = " ".join(str(props.get(key) or "").strip() for key in ("firstName", "lastName")).strip()
    return person or account_id or "Unknown"


def _ms_to_datetime(value: Any) -> datetime | None:
    try:
        if value is None or int(value) <= 0:
            return None
        return datetime.fromtimestamp(int(value) / 1000.0, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def extract_team_maps(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Build a de-duplicated, enriched catalog from CalTopo account data.

    The official account response exposes CollaborativeMap.accountId, folderId and updated,
    plus UserFolder objects, account records and bookmark relations. We keep one row per map ID;
    identical titles with different IDs remain separate because they are distinct CalTopo maps.
    """
    accounts = {str(item.get("id")): item for item in payload.get("accounts", []) if isinstance(item, dict) and item.get("id")}
    folders: dict[str, dict[str, Any]] = {}
    for feature in payload.get("features", []):
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties") or {}
        if props.get("class") == "UserAccount" and feature.get("id"):
            accounts.setdefault(str(feature["id"]), feature)
        if props.get("class") == "UserFolder" and feature.get("id"):
            folders[str(feature["id"])] = feature

    # A bookmark relation tells us in which visible team/account the map is filed.
    bookmark_rels: dict[str, dict[str, Any]] = {}
    for rel in payload.get("rels", []):
        if not isinstance(rel, dict):
            continue
        props = rel.get("properties") or {}
        if props.get("class") == "UserAccountMapRel" and props.get("mapId"):
            bookmark_rels[str(props["mapId"])] = rel

    def folder_chain(folder_id: str | None) -> list[dict[str, str]]:
        chain: list[dict[str, str]] = []
        seen: set[str] = set()
        current = str(folder_id or "")
        while current and current not in seen:
            seen.add(current)
            folder = folders.get(current)
            if not folder:
                chain.append({"id": current, "title": f"Folder {current}"})
                break
            props = folder.get("properties") or {}
            chain.append({"id": current, "title": str(props.get("title") or props.get("name") or current)})
            parent = props.get("folderId") or props.get("parentId") or props.get("parentFolderId")
            current = str(parent or "")
        chain.reverse()
        return chain

    maps_by_id: dict[str, dict[str, Any]] = {}
    for feature in payload.get("features", []):
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties") or {}
        if props.get("class") != "CollaborativeMap" or not feature.get("id"):
            continue
        map_id = str(feature["id"])
        rel = bookmark_rels.get(map_id)
        rel_props = (rel or {}).get("properties") or {}
        owner_id = str(props.get("accountId") or "")
        catalog_account_id = str(rel_props.get("accountId") or owner_id)
        owner_name = _account_display_name(accounts.get(owner_id), owner_id)
        catalog_account_name = _account_display_name(accounts.get(catalog_account_id), catalog_account_id)
        folder_id = str(props.get("folderId") or rel_props.get("folderId") or "") or None
        chain = folder_chain(folder_id)
        updated_values = [props.get("updated"), rel_props.get("mapUpdated")]
        updated_ms = max((int(v) for v in updated_values if v is not None and str(v).isdigit()), default=0)
        item = {
            "id": map_id,
            "title": str(props.get("title") or map_id),
            "account_id": owner_id,
            "owner_name": owner_name,
            "catalog_account_id": catalog_account_id,
            "catalog_account_name": catalog_account_name,
            "folder_id": folder_id,
            "folder_chain": chain,
            "folder_path": " / ".join(part["title"] for part in chain),
            "updated": updated_ms or None,
            "updated_at": _ms_to_datetime(updated_ms),
            "sharing": str(props.get("sharing") or ""),
            "is_bookmark": bool(rel),
        }
        # If CalTopo ever repeats the same map feature in one account response, prefer the newest copy.
        old = maps_by_id.get(map_id)
        if old is None or int(item.get("updated") or 0) >= int(old.get("updated") or 0):
            maps_by_id[map_id] = item

    title_counts: dict[str, int] = {}
    for item in maps_by_id.values():
        key = item["title"].strip().casefold()
        title_counts[key] = title_counts.get(key, 0) + 1
    for item in maps_by_id.values():
        item["same_title_count"] = title_counts.get(item["title"].strip().casefold(), 1)

    return sorted(
        maps_by_id.values(),
        key=lambda item: (item["catalog_account_name"].casefold(), item["folder_path"].casefold(), item["title"].casefold(), item["id"]),
    )


def build_catalog_tree(maps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    roots: dict[str, dict[str, Any]] = {}
    for item in maps:
        account_key = item.get("catalog_account_id") or item.get("account_id") or "unknown"
        root = roots.setdefault(account_key, {
            "id": account_key,
            "name": item.get("catalog_account_name") or account_key,
            "maps": [],
            "folders": {},
        })
        node = root
        for part in item.get("folder_chain") or []:
            folder_id = part.get("id") or part.get("title")
            folders_for_node = node.setdefault("folders", {})
            node = folders_for_node.setdefault(folder_id, {
                "id": folder_id,
                "name": part.get("title") or folder_id,
                "maps": [],
                "folders": {},
            })
        node.setdefault("maps", []).append(item)

    def finalize(node: dict[str, Any]) -> dict[str, Any]:
        node["maps"] = sorted(node.get("maps", []), key=lambda x: (x["title"].casefold(), x["id"]))
        children = [finalize(child) for child in node.get("folders", {}).values()]
        node["children"] = sorted(children, key=lambda x: x["name"].casefold())
        node.pop("folders", None)
        node["map_count"] = len(node["maps"]) + sum(child["map_count"] for child in node["children"])
        return node

    return [finalize(root) for root in sorted(roots.values(), key=lambda x: x["name"].casefold())]


async def refresh_team_catalog(db: Session, team_id: str) -> list[dict[str, Any]]:
    """Fetch all CollaborativeMap objects visible to the configured Service Account.

    The application does not impose a hard-coded CalTopo role requirement. It uses the
    permissions granted to the configured service account and reports permission errors returned by CalTopo.
    """
    client = caltopo_client(db)
    payload = await client.get_team(team_id, 0)
    maps = extract_team_maps(payload)
    for item in maps:
        watch = db.scalar(select(MapWatch).where(MapWatch.map_id == item["id"]))
        if watch and item["title"]:
            watch.title = item["title"]
    db.commit()
    return maps


async def ensure_watch(
    db: Session,
    map_id: str,
    source: str = "manual",
    source_rule_id: int | None = None,
    title: str = "",
    reactivate: bool = False,
) -> MapWatch:
    watch = db.scalar(select(MapWatch).where(MapWatch.map_id == map_id))
    if watch:
        if title:
            watch.title = title
        if reactivate:
            watch.active = True
            watch.auto_pause_at = utcnow() + timedelta(days=AUTO_PAUSE_DAYS)
        return watch
    watch = MapWatch(
        map_id=map_id,
        title=title,
        source=source,
        source_rule_id=source_rule_id,
        active=True,
        auto_pause_at=utcnow() + timedelta(days=AUTO_PAUSE_DAYS),
    )
    db.add(watch)
    db.flush()
    return watch


async def backup_watch(
    db: Session,
    watch: MapWatch,
    force_full: bool = False,
    reason: str = "scheduled",
) -> Snapshot | None:
    ensure_backup_disk_space(db)
    client = caltopo_client(db)
    do_full = force_full or watch.last_server_ts == 0 or watch.poll_count % full_verify_every(db) == 0
    since = 0 if do_full else watch.last_server_ts
    try:
        payload = await client.get_map(watch.map_id, since)
        discovered_title = map_title(payload, watch.map_id)
        if discovered_title and discovered_title != watch.map_id:
            watch.title = discovered_title

        if do_full:
            changes = ingest_full(db, watch.map_id, payload)
        else:
            changes = ingest_incremental(db, watch.map_id, payload)

        server_ts = response_timestamp(payload) or watch.last_server_ts
        snap = create_snapshot_if_changed(
            db,
            watch.map_id,
            server_ts,
            f"{reason}-full" if do_full else reason,
        )
        now = utcnow()
        if changes > 0:
            watch.last_change_at = now
            watch.quiet_snapshot_at = None

        watch.last_server_ts = max(server_ts, watch.last_server_ts)
        watch.poll_count += 1
        watch.last_poll_at = now
        watch.last_success_at = now
        watch.last_error = None
        add_audit(
            db,
            "backup",
            map_id=watch.map_id,
            detail=f"snapshot={snap.id if snap else 'none'}, changes={changes}, full={do_full}",
        )
        db.commit()
        return snap
    except Exception as exc:
        watch.last_poll_at = utcnow()
        watch.last_error = str(exc)[:2000]
        add_audit(db, "backup_error", map_id=watch.map_id, detail=watch.last_error)
        db.commit()
        raise


def maybe_create_quiet_snapshot(db: Session, watch: MapWatch) -> Snapshot | None:
    """Create exactly one closing snapshot 30 minutes after the last detected change."""
    last_change = _aware(watch.last_change_at)
    if last_change is None or watch.quiet_snapshot_at is not None:
        return None
    if utcnow() - last_change < timedelta(minutes=QUIET_SNAPSHOT_MINUTES):
        return None
    ensure_backup_disk_space(db)
    snap = create_snapshot(db, watch.map_id, watch.last_server_ts, "30min-after-last-change")
    watch.quiet_snapshot_at = utcnow()
    add_audit(db, "backup_quiet", map_id=watch.map_id, detail=f"snapshot={snap.id}")
    db.commit()
    return snap


async def discover_rule(db: Session, rule: TeamRule) -> int:
    client = caltopo_client(db)
    try:
        payload = await client.get_team(rule.team_id, 0)
        rx = re.compile(rule.pattern)
        count = 0
        for item in extract_team_maps(payload):
            existing = db.scalar(select(MapWatch).where(MapWatch.map_id == item["id"]))
            if existing and item["title"]:
                existing.title = item["title"]
            if rx.search(item["title"]):
                # Do not reactivate a map that was automatically or manually paused.
                await ensure_watch(db, item["id"], "pattern", rule.id, item["title"], reactivate=False)
                count += 1
        rule.last_server_ts = int(payload.get("timestamp") or 0)
        rule.last_scan_at = utcnow()
        rule.last_error = None
        add_audit(db, "discovery", detail=f"rule={rule.id}, matches={count}")
        db.commit()
        return count
    except Exception as exc:
        rule.last_scan_at = utcnow()
        rule.last_error = str(exc)[:2000]
        add_audit(db, "discovery_error", detail=f"rule={rule.id}: {rule.last_error}")
        db.commit()
        raise


async def pre_restore_snapshot(db: Session, map_id: str) -> Snapshot | None:
    watch = db.scalar(select(MapWatch).where(MapWatch.map_id == map_id))
    if not watch:
        watch = await ensure_watch(db, map_id)
    return await backup_watch(db, watch, force_full=True, reason="pre-restore")


async def restore_one_version(
    db: Session,
    map_id: str,
    feature: dict[str, Any],
    *,
    actor_username: str | None = None,
    actor_role: str | None = None,
    client_ip: str | None = None,
    source_version_id: int | None = None,
) -> str:
    client = caltopo_client(db)
    otype = feature_type(feature)
    if otype not in SUPPORTED_WRITE_TYPES:
        raise ValueError(f"Object type {otype!r} is not writable via the documented CalTopo Marker/Shape API")
    await pre_restore_snapshot(db, map_id)
    oid = str(feature.get("id") or "")
    live = await client.get_map(map_id, 0)
    live_ids = {str(f.get("id")) for f in (live.get("state") or live).get("features", []) if f.get("id") is not None}
    if oid and oid in live_ids:
        await client.edit_object(map_id, otype, oid, feature)
        action = "edited"
    else:
        await client.add_object(map_id, otype, feature)
        action = "re-created"
    add_audit(
        db,
        "restore_object",
        map_id=map_id,
        object_id=oid or None,
        object_title=feature_title(feature) or None,
        detail=f"result={action}, version={source_version_id or ''}",
        actor_username=actor_username,
        actor_role=actor_role,
        client_ip=client_ip,
    )
    db.commit()
    watch = db.scalar(select(MapWatch).where(MapWatch.map_id == map_id))
    if watch:
        try:
            await backup_watch(db, watch, force_full=True, reason="post-restore")
        except Exception as exc:
            add_audit(
                db, "post_restore_backup_error", map_id=map_id, object_id=oid or None,
                object_title=feature_title(feature) or None, detail=str(exc)[:2000], actor_username=actor_username, actor_role=actor_role, client_ip=client_ip,
            )
            db.commit()
    return action


async def restore_snapshot(
    db: Session,
    snapshot: Snapshot,
    *,
    actor_username: str | None = None,
    actor_role: str | None = None,
    client_ip: str | None = None,
) -> dict[str, int]:
    map_id = snapshot.map_id
    client = caltopo_client(db)
    await pre_restore_snapshot(db, map_id)
    live_payload = await client.get_map(map_id, 0)
    live_state = live_payload.get("state") or live_payload
    target = snapshot_state(snapshot)
    plan = diff_states(target, live_state)
    stats = {"changed": 0, "restored": 0, "removed": 0, "skipped": 0, "errors": 0}
    for item in plan:
        if item.object_type not in SUPPORTED_WRITE_TYPES:
            stats["skipped"] += 1
            continue
        try:
            if item.status == "change" and item.target is not None:
                await client.edit_object(map_id, item.object_type, item.object_id, item.target)
                stats["changed"] += 1
            elif item.status == "restore" and item.target is not None:
                await client.add_object(map_id, item.object_type, item.target)
                stats["restored"] += 1
            elif item.status == "remove":
                await client.delete_object(map_id, item.object_type, item.object_id)
                stats["removed"] += 1
        except Exception as exc:
            stats["errors"] += 1
            add_audit(
                db,
                "restore_error",
                map_id=map_id,
                object_id=item.object_id,
                object_title=item.title or None,
                detail=str(exc)[:2000],
                actor_username=actor_username,
                actor_role=actor_role,
                client_ip=client_ip,
            )
    add_audit(
        db,
        "restore_snapshot",
        map_id=map_id,
        object_title="Entire map",
        detail=f"snapshot={snapshot.id}, stats={json.dumps(stats, sort_keys=True)}",
        actor_username=actor_username,
        actor_role=actor_role,
        client_ip=client_ip,
    )
    db.commit()
    watch = db.scalar(select(MapWatch).where(MapWatch.map_id == map_id))
    if watch:
        try:
            await backup_watch(db, watch, force_full=True, reason="post-restore")
        except Exception as exc:
            add_audit(
                db, "post_restore_backup_error", map_id=map_id, object_title="Entire map",
                detail=f"snapshot={snapshot.id}, error={str(exc)[:1800]}",
                actor_username=actor_username, actor_role=actor_role, client_ip=client_ip,
            )
            db.commit()
    return stats
