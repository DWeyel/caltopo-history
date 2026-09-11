from pathlib import Path


def replace(path, old, new):
    p = Path(path)
    s = p.read_text()
    if old not in s:
        raise SystemExit(f'match not found in {path}: {old[:120]!r}')
    p.write_text(s.replace(old, new, 1))

# Structured CalTopo errors + documented whole-map create endpoint.
replace('app/caltopo.py',
'''class CalTopoError(RuntimeError):
    pass
''',
'''class CalTopoError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, response_text: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
''')
replace('app/caltopo.py',
'''        if response.status_code >= 400:
            raise CalTopoError(f"CalTopo API {response.status_code}: {response.text[:500]}")
''',
'''        if response.status_code >= 400:
            text = response.text[:500]
            raise CalTopoError(
                f"CalTopo API {response.status_code}: {text}",
                status_code=response.status_code,
                response_text=text,
            )
''')
replace('app/caltopo.py',
'''    async def get_team(self, team_id: str, since: int = 0) -> dict[str, Any]:
        return await self.request("GET", f"/api/v1/acct/{team_id}/since/{since}")

''',
'''    async def get_team(self, team_id: str, since: int = 0) -> dict[str, Any]:
        return await self.request("GET", f"/api/v1/acct/{team_id}/since/{since}")

    async def create_map(self, team_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a CollaborativeMap using CalTopo's documented Team API."""
        return await self.request("POST", f"/api/v1/acct/{team_id}/CollaborativeMap", payload)

''')

# Persist map ownership/properties on watches and snapshots so a deleted map can be recreated.
replace('app/db.py',
'''    title: Mapped[str] = mapped_column(String(300), default="")
    source: Mapped[str] = mapped_column(String(32), default="manual")
''',
'''    title: Mapped[str] = mapped_column(String(300), default="")
    team_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    map_properties_gz: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="manual")
''')
replace('app/db.py',
'''    reason: Mapped[str] = mapped_column(String(80), default="scheduled")
    object_count: Mapped[int] = mapped_column(Integer, default=0)
    state_gz: Mapped[bytes] = mapped_column(LargeBinary)
''',
'''    reason: Mapped[str] = mapped_column(String(80), default="scheduled")
    object_count: Mapped[int] = mapped_column(Integer, default=0)
    map_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    team_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    map_properties_gz: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    state_gz: Mapped[bytes] = mapped_column(LargeBinary)
''')
replace('app/db.py',
'''            additions = {
                "poll_interval_seconds": "INTEGER",
                "last_change_at": "DATETIME",
                "quiet_snapshot_at": "DATETIME",
                "auto_pause_at": "DATETIME",
            }
''',
'''            additions = {
                "poll_interval_seconds": "INTEGER",
                "last_change_at": "DATETIME",
                "quiet_snapshot_at": "DATETIME",
                "auto_pause_at": "DATETIME",
                "team_id": "VARCHAR(32)",
                "map_properties_gz": "BLOB",
            }
''')
# Add snapshot migrations after map_watches migration block.
replace('app/db.py',
'''            conn.execute(text(
                "UPDATE map_watches SET auto_pause_at = datetime(created_at, '+7 days') "
                "WHERE auto_pause_at IS NULL"
            ))


def _bootstrap_admin() -> None:
''',
'''            conn.execute(text(
                "UPDATE map_watches SET auto_pause_at = datetime(created_at, '+7 days') "
                "WHERE auto_pause_at IS NULL"
            ))

        if "snapshots" in table_names:
            columns = {column["name"] for column in inspector.get_columns("snapshots")}
            additions = {
                "map_title": "VARCHAR(300)",
                "team_id": "VARCHAR(32)",
                "map_properties_gz": "BLOB",
            }
            for name, sql_type in additions.items():
                if name not in columns:
                    conn.execute(text(f"ALTER TABLE snapshots ADD COLUMN {name} {sql_type}"))


def _bootstrap_admin() -> None:
''')

# Snapshot metadata capture.
replace('app/history.py',
'''from .db import CurrentObject, ObjectVersion, Snapshot, utcnow
''',
'''from .db import CurrentObject, MapWatch, ObjectVersion, Snapshot, utcnow
''')
replace('app/history.py',
'''def create_snapshot(db: Session, map_id: str, server_ts: int, reason: str) -> Snapshot:
    state = current_state(db, map_id)
    snap = Snapshot(
        map_id=map_id,
        server_timestamp=server_ts,
        reason=reason,
        object_count=len(state["features"]),
        state_gz=pack_json(state),
    )
''',
'''def _snapshot_metadata(db: Session, map_id: str) -> dict[str, Any]:
    watch = db.scalar(select(MapWatch).where(MapWatch.map_id == map_id))
    if watch is None:
        return {}
    return {
        "map_title": watch.title or None,
        "team_id": watch.team_id or None,
        "map_properties_gz": watch.map_properties_gz,
    }


def create_snapshot(db: Session, map_id: str, server_ts: int, reason: str) -> Snapshot:
    state = current_state(db, map_id)
    snap = Snapshot(
        map_id=map_id,
        server_timestamp=server_ts,
        reason=reason,
        object_count=len(state["features"]),
        state_gz=pack_json(state),
        **_snapshot_metadata(db, map_id),
    )
''')
replace('app/history.py',
'''    snap = Snapshot(
        map_id=map_id,
        server_timestamp=server_ts,
        reason=reason,
        object_count=len(state["features"]),
        state_gz=pack_json(state),
    )
''',
'''    snap = Snapshot(
        map_id=map_id,
        server_timestamp=server_ts,
        reason=reason,
        object_count=len(state["features"]),
        state_gz=pack_json(state),
        **_snapshot_metadata(db, map_id),
    )
''')

# Service metadata synchronization and deleted-map recreation.
replace('app/services.py', 'from .caltopo import CalTopoClient\n', 'from .caltopo import CalTopoClient, CalTopoError\n')
replace('app/services.py',
'''    map_title,
    response_timestamp,
    snapshot_state,
)''',
'''    map_title,
    pack_json,
    response_timestamp,
    snapshot_state,
    unpack_json,
)''')
replace('app/services.py',
'''            "sharing": str(props.get("sharing") or ""),
            "locked": props.get("locked") is True,
''',
'''            "sharing": str(props.get("sharing") or ""),
            "locked": props.get("locked") is True,
            "map_properties": dict(props),
''')
replace('app/services.py',
'''        if watch and item["title"]:
            watch.title = item["title"]
        if watch and watch.active and item["locked"] and pause_when_locked(db):
''',
'''        if watch:
            if item["title"]:
                watch.title = item["title"]
            watch.team_id = item.get("account_id") or watch.team_id
            watch.map_properties_gz = pack_json(item.get("map_properties") or {})
        if watch and watch.active and item["locked"] and pause_when_locked(db):
''')
replace('app/services.py',
'''    title: str = "",
    reactivate: bool = False,
) -> MapWatch:
''',
'''    title: str = "",
    reactivate: bool = False,
    team_id: str | None = None,
    map_properties: dict[str, Any] | None = None,
) -> MapWatch:
''')
replace('app/services.py',
'''        if title:
            watch.title = title
        if reactivate:
''',
'''        if title:
            watch.title = title
        if team_id:
            watch.team_id = team_id
        if map_properties is not None:
            watch.map_properties_gz = pack_json(map_properties)
        if reactivate:
''')
replace('app/services.py',
'''        active=True,
        auto_pause_at=utcnow() + timedelta(days=AUTO_PAUSE_DAYS),
    )
''',
'''        active=True,
        team_id=team_id,
        map_properties_gz=pack_json(map_properties) if map_properties is not None else None,
        auto_pause_at=utcnow() + timedelta(days=AUTO_PAUSE_DAYS),
    )
''')
replace('app/services.py',
'''                await ensure_watch(db, item["id"], "pattern", rule.id, item["title"], reactivate=False)
''',
'''                await ensure_watch(
                    db, item["id"], "pattern", rule.id, item["title"], reactivate=False,
                    team_id=item.get("account_id"), map_properties=item.get("map_properties"),
                )
''')

# Replace restore_snapshot with a version that recreates a deleted map when metadata is available.
p = Path('app/services.py')
s = p.read_text()
start = s.index('async def restore_snapshot(\n')
new_func = r'''def _created_map_id(payload: dict[str, Any]) -> str:
    for value in (
        payload.get("id"), payload.get("mapId"), payload.get("map_id"),
        (payload.get("map") or {}).get("id") if isinstance(payload.get("map"), dict) else None,
        (payload.get("feature") or {}).get("id") if isinstance(payload.get("feature"), dict) else None,
    ):
        if value:
            return str(value)
    return ""


def _create_map_properties(snapshot: Snapshot, watch: MapWatch | None) -> tuple[str, str, dict[str, Any]]:
    team_id = str(snapshot.team_id or (watch.team_id if watch else "") or "").strip()
    title = str(snapshot.map_title or (watch.title if watch else "") or snapshot.map_id).strip()
    packed = snapshot.map_properties_gz or (watch.map_properties_gz if watch else None)
    source = unpack_json(packed) if packed else {}
    if not isinstance(source, dict):
        source = {}
    if not team_id:
        raise ValueError(
            "Cannot recreate this deleted map automatically because its owning CalTopo Team ID was not recorded. "
            "This can affect snapshots created before map metadata capture was available."
        )
    properties: dict[str, Any] = {
        "title": title,
        "mode": str(source.get("mode") or "cal"),
        "sharing": str(source.get("sharing") or "SECRET"),
    }
    config = source.get("mapConfig") or source.get("config")
    if config:
        properties["mapConfig"] = config if isinstance(config, str) else json.dumps(config, separators=(",", ":"))
    if source.get("description") is not None:
        properties["description"] = source.get("description")
    return team_id, title, properties


def _create_map_state(snapshot: Snapshot) -> tuple[dict[str, Any], int]:
    features: list[dict[str, Any]] = []
    skipped = 0
    for feature in snapshot_state(snapshot).get("features", []):
        if feature_type(feature) not in SUPPORTED_WRITE_TYPES:
            skipped += 1
            continue
        geometry_type = str((feature.get("geometry") or {}).get("type") or "")
        if geometry_type not in {"Point", "LineString", "Polygon"}:
            skipped += 1
            continue
        clean = json.loads(json.dumps(feature))
        clean.pop("id", None)
        if isinstance(clean.get("properties"), dict):
            clean["properties"].pop("class", None)
        features.append(clean)
    return {"type": "FeatureCollection", "features": features}, skipped


async def _recreate_deleted_map(
    db: Session,
    snapshot: Snapshot,
    client: CalTopoClient,
    *,
    actor_username: str | None,
    actor_role: str | None,
    client_ip: str | None,
) -> dict[str, Any]:
    old_watch = db.scalar(select(MapWatch).where(MapWatch.map_id == snapshot.map_id))
    team_id, title, properties = _create_map_properties(snapshot, old_watch)
    state, skipped = _create_map_state(snapshot)
    result = await client.create_map(team_id, {"properties": properties, "state": state})
    new_map_id = _created_map_id(result)
    if not new_map_id:
        # The documented create endpoint normally returns the new object. Fall back to the
        # account catalog and select the newest exact title match owned by the destination team.
        catalog = extract_team_maps(await client.get_team(team_id, 0))
        matches = [item for item in catalog if item.get("account_id") == team_id and item.get("title") == title]
        if matches:
            matches.sort(key=lambda item: int(item.get("updated") or 0), reverse=True)
            new_map_id = str(matches[0]["id"])
    if not new_map_id:
        raise ValueError("CalTopo created the map but did not return a new Map ID, and it could not be resolved from the team catalog.")

    if old_watch is not None:
        old_watch.active = False
        replacement = await ensure_watch(
            db, new_map_id, source="recreated", title=title, reactivate=True,
            team_id=team_id, map_properties={**(unpack_json(old_watch.map_properties_gz) if old_watch.map_properties_gz else {}), **properties},
        )
        replacement.poll_interval_seconds = old_watch.poll_interval_seconds

    stats: dict[str, Any] = {
        "changed": 0,
        "restored": len(state["features"]),
        "removed": 0,
        "skipped": skipped,
        "errors": 0,
        "recreated_map": 1,
        "new_map_id": new_map_id,
    }
    add_audit(
        db,
        "restore_snapshot_recreated_map",
        map_id=snapshot.map_id,
        object_title="Entire map",
        detail=f"snapshot={snapshot.id}, new_map_id={new_map_id}, team_id={team_id}, stats={json.dumps(stats, sort_keys=True)}",
        actor_username=actor_username,
        actor_role=actor_role,
        client_ip=client_ip,
    )
    db.commit()
    return stats


async def restore_snapshot(
    db: Session,
    snapshot: Snapshot,
    *,
    actor_username: str | None = None,
    actor_role: str | None = None,
    client_ip: str | None = None,
) -> dict[str, Any]:
    map_id = snapshot.map_id
    client = caltopo_client(db)
    try:
        live_payload = await client.get_map(map_id, 0)
    except CalTopoError as exc:
        if exc.status_code == 404:
            return await _recreate_deleted_map(
                db, snapshot, client,
                actor_username=actor_username, actor_role=actor_role, client_ip=client_ip,
            )
        raise

    # A live map is about to be modified: preserve the current server state first.
    await pre_restore_snapshot(db, map_id)
    live_state = live_payload.get("state") or live_payload
    target = snapshot_state(snapshot)
    plan = diff_states(target, live_state)
    stats: dict[str, Any] = {"changed": 0, "restored": 0, "removed": 0, "skipped": 0, "errors": 0, "error_details": []}
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
            detail = str(exc)[:500]
            stats["error_details"].append(detail)
            add_audit(
                db,
                "restore_error",
                map_id=map_id,
                object_id=item.object_id,
                object_title=item.title or None,
                detail=detail,
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
'''
p.write_text(s[:start] + new_func + '\n')

# Main map picker stores catalog metadata, and route reports recreation explicitly.
replace('app/main.py',
'''        await ensure_watch(db, map_id, source="picker", title=by_id[map_id]["title"], reactivate=(before is None))
''',
'''        await ensure_watch(
            db, map_id, source="picker", title=by_id[map_id]["title"], reactivate=(before is None),
            team_id=by_id[map_id].get("account_id"), map_properties=by_id[map_id].get("map_properties"),
        )
''')
replace('app/main.py',
'''        flash_t(
            request, db, "rollback_incomplete" if stats["errors"] else "rollback_done", "success" if not stats["errors"] else "warning",
            stats=", ".join([
''',
'''        message_key = "deleted_map_recreated" if stats.get("recreated_map") else ("rollback_incomplete" if stats["errors"] else "rollback_done")
        level = "warning" if stats["errors"] or stats.get("skipped", 0) else "success"
        flash_t(
            request, db, message_key, level,
            map_id=stats.get("new_map_id", ""),
            stats=", ".join([
''')

# Update EN/DE recovery guidance and add recreation message.
replace('app/i18n.py',
'''        "archive_history_help": "This map is archived locally and is not monitored. You can browse, compare, download and restore retained history without restarting monitoring. Restoring requires the original CalTopo map to exist, be unlocked and be writable. To monitor again, add its Map ID from the dashboard.",
''',
'''        "archive_history_help": "This map is archived locally and is not monitored. You can browse, compare, download and restore retained history without restarting monitoring. If the original map was deleted, snapshots that contain recorded Team metadata can recreate it as a new CalTopo map with a new Map ID.",
''')
replace('app/i18n.py',
'''        "restore_map_to_time": "Roll back objects in the existing map",
        "restore_map_explanation": "The app first creates a fresh pre-restore snapshot. It then updates, recreates or removes supported marker/shape objects. Unsupported object types are skipped and recorded in the audit log.",
''',
'''        "restore_map_to_time": "Roll back or recreate this map",
        "restore_map_explanation": "If the map still exists, the app first creates a fresh pre-restore snapshot and then updates, recreates or removes supported marker/shape objects. If the map was deleted and its Team metadata was recorded, CalTopo History creates a new map from the snapshot. CalTopo assigns a new Map ID.",
''')
replace('app/i18n.py',
'''        "restore_requirements": "The original CalTopo map must still exist, be unlocked and allow this service account to write. Rollback does not recreate a deleted map or restore map settings/sharing. For a deleted map, download the snapshot GeoJSON and import supported objects into a new map in CalTopo. For a locked map, ask a team manager or admin to unlock it before retrying. Writes are not atomic: some changes may succeed before an error occurs. Review the restore audit before retrying.",
        "rollback_incomplete": "Rollback finished with errors; some changes may have been applied. Review the restore audit and check that the map is unlocked and writable before retrying: {stats}",
''',
'''        "restore_requirements": "Existing maps must be unlocked and writable by the service account. Deleted maps can be recreated only when the snapshot contains the owning Team metadata; the recreated map receives a new CalTopo Map ID. Map creation restores supported marker/shape geometry plus recorded title/mode/sharing/layer configuration, but you should review the new map before operational use. Writes to existing maps are not atomic: some changes may succeed before an error occurs.",
        "rollback_incomplete": "Rollback finished with errors; some changes may have been applied. Review the restore audit. A locked map or insufficient UPDATE permission can cause these failures: {stats}",
        "deleted_map_recreated": "The deleted map was recreated as new CalTopo map {map_id}. CalTopo assigned a new Map ID; review the new map's sharing/settings before operational use. {stats}",
''')
# German strings (exact current text may differ; insert near rollback key if the long old requirement is not stable).
p = Path('app/i18n.py')
s = p.read_text()
if '"deleted_map_recreated":' not in s[s.index('"de": {'):]:
    de_pos = s.index('"de": {')
    key_pos = s.index('        "rollback_incomplete":', de_pos)
    s = s[:key_pos] + '        "deleted_map_recreated": "Die gelöschte Karte wurde als neue CalTopo-Karte {map_id} wiederhergestellt. CalTopo hat eine neue Map-ID vergeben; bitte Freigabe und Einstellungen vor dem operativen Einsatz prüfen. {stats}",\n' + s[key_pos:]
# Replace common German limitation phrases if present.
s = s.replace('"restore_map_to_time": "Objekte in der bestehenden Karte zurücksetzen"', '"restore_map_to_time": "Karte zurücksetzen oder neu erstellen"')
s = s.replace('Rollback stellt keine gelöschte Karte wieder her', 'Gelöschte Karten können bei vorhandenen Team-Metadaten als neue Karte mit neuer Map-ID wiederhergestellt werden')
p.write_text(s)

# Release notes: this feature is now part of the unreleased 1.1.0.
p = Path('RELEASE-NOTES-v1.1.0.md')
s = p.read_text()
s = s.replace('- Clarified that rollback operates on Marker/Shape objects within the original existing, unlocked and writable map. It does not recreate a deleted map, restore sharing settings or bypass locks.\n', '- Whole-map recovery can now recreate a deleted CalTopo map through the documented Team API when the backup contains the original owning Team metadata. CalTopo assigns a new Map ID.\n- Snapshots now retain the map title, owning Team ID and map properties needed for future deleted-map recovery. Existing-map rollback still requires an unlocked, writable map.\n')
s = s.replace('## Upgrade\n\nExisting watches, history and settings remain in place. No database schema migration is required.', '## Upgrade\n\nExisting watches, history and settings remain in place. The SQLite schema is migrated automatically to add nullable map metadata fields for future recovery. Older snapshots remain readable, but a deleted map can only be recreated automatically when its Team metadata is available.')
if '## Recovery limits' in s:
    s = s[:s.index('## Recovery limits')] + '''## Recovery limits\n\nA deleted map is recreated as a new CalTopo map; the original Map ID cannot be restored. Automatic recreation requires recorded owning-Team metadata. Older snapshots without that metadata remain available for GeoJSON download/manual recovery. Existing-map restore writes can partially succeed; locked maps or insufficient UPDATE permission are reported in the restore audit.\n\nNo live CalTopo map was modified during release testing.\n'''
p.write_text(s)
