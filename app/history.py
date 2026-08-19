from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from .db import CurrentObject, ObjectVersion, Snapshot, utcnow


def pack_json(value: Any) -> bytes:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return gzip.compress(raw, compresslevel=6)


def unpack_json(value: bytes | None) -> Any:
    if value is None:
        return None
    return json.loads(gzip.decompress(value).decode("utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def feature_type(feature: dict[str, Any]) -> str:
    props = feature.get("properties") or {}
    cls = props.get("class")
    if cls:
        return str(cls)
    geom = (feature.get("geometry") or {}).get("type")
    if geom == "Point":
        return "Marker"
    if geom in {"LineString", "Polygon", "MultiLineString", "MultiPolygon"}:
        return "Shape"
    return "Unknown"


def feature_title(feature: dict[str, Any]) -> str:
    return str((feature.get("properties") or {}).get("title") or "")


def feature_updated_at(feature: dict[str, Any]) -> datetime:
    props = feature.get("properties") or {}
    raw = props.get("updated") or feature.get("updated")
    if raw is not None:
        try:
            value = float(raw)
            if value > 10_000_000_000:
                value /= 1000.0
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            pass
    return utcnow()


def map_title(payload: dict[str, Any], map_id: str = "") -> str:
    map_obj = payload.get("map") if isinstance(payload.get("map"), dict) else None
    candidates = [payload, payload.get("properties"), payload.get("metadata"), payload.get("meta"), map_obj, map_obj.get("properties") if map_obj else None]
    for props in candidates:
        if isinstance(props, dict) and props.get("title"):
            return str(props["title"])
    for collection_name in ("features", "maps"):
        collection = payload.get(collection_name)
        if not isinstance(collection, list):
            continue
        for feature in collection:
            if not isinstance(feature, dict):
                continue
            props = feature.get("properties") or {}
            if props.get("class") == "CollaborativeMap" and (not map_id or str(feature.get("id")) == map_id) and props.get("title"):
                return str(props["title"])
    return ""


def normalize_state(payload: dict[str, Any]) -> dict[str, Any]:
    state = payload.get("state") or payload
    if state.get("type") == "FeatureCollection":
        return {"type": "FeatureCollection", "features": state.get("features", [])}
    return {"type": "FeatureCollection", "features": state.get("features", [])}


def response_timestamp(payload: dict[str, Any]) -> int:
    return int(payload.get("timestamp") or (payload.get("state") or {}).get("timestamp") or 0)


def response_ids(payload: dict[str, Any]) -> dict[str, list[str]] | None:
    ids = payload.get("ids")
    if ids is None and isinstance(payload.get("state"), dict):
        ids = payload["state"].get("ids")
    return ids if isinstance(ids, dict) else None


def current_state(db: Session, map_id: str) -> dict[str, Any]:
    rows = db.scalars(select(CurrentObject).where(CurrentObject.map_id == map_id).order_by(CurrentObject.id)).all()
    return {"type": "FeatureCollection", "features": [unpack_json(r.feature_gz) for r in rows]}


def create_snapshot(db: Session, map_id: str, server_ts: int, reason: str) -> Snapshot:
    state = current_state(db, map_id)
    snap = Snapshot(map_id=map_id, server_timestamp=server_ts, reason=reason, object_count=len(state["features"]), state_gz=pack_json(state))
    db.add(snap); db.flush(); return snap


def create_snapshot_if_changed(db: Session, map_id: str, server_ts: int, reason: str) -> Snapshot | None:
    state = current_state(db, map_id)
    latest = db.scalar(select(Snapshot).where(Snapshot.map_id == map_id).order_by(Snapshot.captured_at.desc(), Snapshot.id.desc()).limit(1))
    if latest is not None and canonical(snapshot_state(latest)) == canonical(state):
        return None
    snap = Snapshot(map_id=map_id, server_timestamp=server_ts, reason=reason, object_count=len(state["features"]), state_gz=pack_json(state))
    db.add(snap); db.flush(); return snap


def _upsert_feature(db: Session, map_id: str, feature: dict[str, Any], server_ts: int) -> bool:
    object_id = str(feature.get("id") or "")
    if not object_id:
        return False
    row = db.scalar(select(CurrentObject).where(and_(CurrentObject.map_id == map_id, CurrentObject.object_id == object_id)))
    ftype = feature_type(feature); title = feature_title(feature); packed = pack_json(feature)
    if row and canonical(unpack_json(row.feature_gz)) == canonical(feature):
        return False
    db.add(ObjectVersion(map_id=map_id, object_id=object_id, object_type=ftype, title=title, server_timestamp=server_ts, deleted=False, feature_gz=packed))
    if row:
        row.object_type = ftype; row.title = title; row.feature_gz = packed; row.updated_at = feature_updated_at(feature)
    else:
        db.add(CurrentObject(map_id=map_id, object_id=object_id, object_type=ftype, title=title, feature_gz=packed, updated_at=feature_updated_at(feature)))
    return True


def _delete_current(db: Session, row: CurrentObject, server_ts: int) -> None:
    db.add(ObjectVersion(map_id=row.map_id, object_id=row.object_id, object_type=row.object_type, title=row.title, server_timestamp=server_ts, deleted=True, feature_gz=None))
    db.delete(row)


def ingest_full(db: Session, map_id: str, payload: dict[str, Any]) -> int:
    state = normalize_state(payload); ts = response_timestamp(payload)
    incoming = {str(f.get("id")): f for f in state.get("features", []) if f.get("id") is not None}
    existing = db.scalars(select(CurrentObject).where(CurrentObject.map_id == map_id)).all(); changes = 0
    for feature in incoming.values(): changes += int(_upsert_feature(db, map_id, feature, ts))
    for row in existing:
        if row.object_id not in incoming: _delete_current(db, row, ts); changes += 1
    db.flush(); return changes


def ingest_incremental(db: Session, map_id: str, payload: dict[str, Any]) -> int:
    state = normalize_state(payload); ts = response_timestamp(payload); changes = 0
    for feature in state.get("features", []): changes += int(_upsert_feature(db, map_id, feature, ts))
    ids = response_ids(payload)
    if ids:
        for cls, server_ids in ids.items():
            server_set = {str(x) for x in server_ids}
            rows = db.scalars(select(CurrentObject).where(and_(CurrentObject.map_id == map_id, CurrentObject.object_type == cls))).all()
            for row in rows:
                if row.object_id not in server_set: _delete_current(db, row, ts); changes += 1
    db.flush(); return changes


def snapshot_state(snapshot: Snapshot) -> dict[str, Any]: return unpack_json(snapshot.state_gz)


@dataclass
class DiffItem:
    object_id: str; object_type: str; title: str; status: str; target: dict[str, Any] | None; current: dict[str, Any] | None


def diff_states(target: dict[str, Any], current: dict[str, Any]) -> list[DiffItem]:
    t = {str(f.get("id")): f for f in target.get("features", []) if f.get("id") is not None}; c = {str(f.get("id")): f for f in current.get("features", []) if f.get("id") is not None}; out=[]
    for oid in sorted(set(t) | set(c)):
        tf, cf = t.get(oid), c.get(oid); probe = tf or cf or {}
        if tf is None: status="remove"
        elif cf is None: status="restore"
        elif canonical(tf) != canonical(cf): status="change"
        else: continue
        out.append(DiffItem(oid, feature_type(probe), feature_title(probe), status, tf, cf))
    return out


@dataclass
class ObjectOverviewItem:
    object_id: str; object_type: str; title: str; exists_now: bool; restored: bool; status: str; last_change_at: datetime | None


def object_overview(db: Session, map_id: str) -> list[ObjectOverviewItem]:
    current_rows = {row.object_id: row for row in db.scalars(select(CurrentObject).where(CurrentObject.map_id == map_id)).all()}
    versions = db.scalars(select(ObjectVersion).where(ObjectVersion.map_id == map_id).order_by(ObjectVersion.object_id, ObjectVersion.id)).all(); by_object={}
    for version in versions: by_object.setdefault(version.object_id, []).append(version)
    out=[]
    for oid in set(current_rows) | set(by_object):
        current=current_rows.get(oid); ovs=by_object.get(oid,[]); latest=ovs[-1] if ovs else None
        was_deleted=any(v.deleted for v in ovs[:-1] if latest is not None) or (current is not None and any(v.deleted for v in ovs)); exists_now=current is not None; restored=exists_now and was_deleted and latest is not None and not latest.deleted
        out.append(ObjectOverviewItem(oid, current.object_type if current else (latest.object_type if latest else "Unknown"), current.title if current else (latest.title if latest else ""), exists_now, restored, "restored" if restored else ("present" if exists_now else "deleted"), latest.captured_at if latest else (current.updated_at if current else None)))
    return sorted(out,key=lambda item:(item.status=="deleted",item.object_type.lower(),item.title.lower(),item.object_id))


@dataclass
class SnapshotCompareItem:
    object_id: str; object_type: str; title: str; status: str; left: dict[str, Any] | None; right: dict[str, Any] | None


def compare_states(left: dict[str, Any], right: dict[str, Any], include_unchanged: bool=False) -> list[SnapshotCompareItem]:
    a={str(f.get("id")):f for f in left.get("features",[]) if f.get("id") is not None}; b={str(f.get("id")):f for f in right.get("features",[]) if f.get("id") is not None}; out=[]
    for oid in sorted(set(a)|set(b)):
        af,bf=a.get(oid),b.get(oid); probe=bf or af or {}
        if af is None: status="added"
        elif bf is None: status="removed"
        elif canonical(af)!=canonical(bf): status="changed"
        else:
            status="unchanged"
            if not include_unchanged: continue
        out.append(SnapshotCompareItem(oid,feature_type(probe),feature_title(probe),status,af,bf))
    return out
