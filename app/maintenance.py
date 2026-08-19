from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Iterable

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .config import settings
from .db import CurrentObject, MapWatch, ObjectVersion, Snapshot, engine, utcnow


@dataclass
class MapStorage:
    map_id: str
    title: str
    watched: bool
    snapshot_count: int
    snapshot_bytes: int
    version_count: int
    version_bytes: int
    current_count: int
    current_bytes: int

    @property
    def logical_bytes(self) -> int:
        return self.snapshot_bytes + self.version_bytes + self.current_bytes


@dataclass
class DatabaseBackupFile:
    name: str
    size: int
    modified_at: float


@dataclass
class StorageOverview:
    maps: list[MapStorage]
    snapshot_count: int
    snapshot_bytes: int
    version_count: int
    version_bytes: int
    current_count: int
    current_bytes: int
    database_bytes: int
    database_backup_bytes: int
    tool_data_bytes: int
    database_backups: list[DatabaseBackupFile]

    @property
    def logical_bytes(self) -> int:
        return self.snapshot_bytes + self.version_bytes + self.current_bytes


def _sum_blob_bytes(db: Session, model, blob_column, map_id: str | None = None) -> tuple[int, int]:
    stmt = select(func.count(model.id), func.coalesce(func.sum(func.length(blob_column)), 0))
    if map_id is not None:
        stmt = stmt.where(model.map_id == map_id)
    count, size = db.execute(stmt).one()
    return int(count or 0), int(size or 0)


def _database_path() -> Path | None:
    prefix = "sqlite:///"
    if not settings.database_url.startswith(prefix):
        return None
    raw = settings.database_url[len(prefix):]
    # sqlite:////absolute/path -> raw starts with /; sqlite:///relative.db -> relative path.
    return Path(raw).expanduser().resolve()


def database_files_size() -> int:
    path = _database_path()
    if path is None:
        return 0
    total = 0
    for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        try:
            total += candidate.stat().st_size
        except FileNotFoundError:
            pass
    return total


def database_backup_files() -> list[DatabaseBackupFile]:
    path = _database_path()
    if path is None or not path.parent.exists():
        return []
    prefix = path.name + "."
    out: list[DatabaseBackupFile] = []
    for candidate in path.parent.iterdir():
        if not candidate.is_file():
            continue
        if not candidate.name.startswith(prefix) or not candidate.name.endswith(".bak"):
            continue
        stat = candidate.stat()
        out.append(DatabaseBackupFile(candidate.name, stat.st_size, stat.st_mtime))
    return sorted(out, key=lambda item: item.modified_at, reverse=True)


def tool_data_size() -> int:
    return database_files_size() + sum(item.size for item in database_backup_files())


def delete_database_backup(filename: str) -> int:
    path = _database_path()
    if path is None:
        raise ValueError("No SQLite database path configured")
    if Path(filename).name != filename:
        raise ValueError("Invalid backup filename")
    if not filename.startswith(path.name + ".") or not filename.endswith(".bak"):
        raise ValueError("File is not a managed database backup")
    candidate = path.parent / filename
    if not candidate.is_file():
        raise ValueError("Backup file not found")
    size = candidate.stat().st_size
    candidate.unlink()
    return size


def map_storage(db: Session, map_id: str) -> MapStorage:
    watch = db.scalar(select(MapWatch).where(MapWatch.map_id == map_id))
    snapshot_count, snapshot_bytes = _sum_blob_bytes(db, Snapshot, Snapshot.state_gz, map_id)
    version_count, version_bytes = _sum_blob_bytes(db, ObjectVersion, ObjectVersion.feature_gz, map_id)
    current_count, current_bytes = _sum_blob_bytes(db, CurrentObject, CurrentObject.feature_gz, map_id)
    return MapStorage(map_id=map_id,title=(watch.title if watch and watch.title else map_id),watched=watch is not None,snapshot_count=snapshot_count,snapshot_bytes=snapshot_bytes,version_count=version_count,version_bytes=version_bytes,current_count=current_count,current_bytes=current_bytes)


def storage_overview(db: Session) -> StorageOverview:
    watches = {w.map_id: w for w in db.scalars(select(MapWatch)).all()}
    def grouped(model, blob_column):
        rows = db.execute(select(model.map_id, func.count(model.id), func.coalesce(func.sum(func.length(blob_column)), 0)).group_by(model.map_id)).all()
        return {str(mid): (int(count or 0), int(size or 0)) for mid, count, size in rows}
    snapshots, versions, current = grouped(Snapshot, Snapshot.state_gz), grouped(ObjectVersion, ObjectVersion.feature_gz), grouped(CurrentObject, CurrentObject.feature_gz)
    map_ids = set(watches) | set(snapshots) | set(versions) | set(current)
    rows=[]
    for map_id in sorted(map_ids, key=lambda mid: ((watches.get(mid).title if watches.get(mid) else "") or mid).lower()):
        watch=watches.get(map_id); sc,sb=snapshots.get(map_id,(0,0)); vc,vb=versions.get(map_id,(0,0)); cc,cb=current.get(map_id,(0,0))
        rows.append(MapStorage(map_id,(watch.title if watch and watch.title else map_id),watch is not None,sc,sb,vc,vb,cc,cb))
    return StorageOverview(rows,sum(r.snapshot_count for r in rows),sum(r.snapshot_bytes for r in rows),sum(r.version_count for r in rows),sum(r.version_bytes for r in rows),sum(r.current_count for r in rows),sum(r.current_bytes for r in rows),database_files_size(),sum(item.size for item in database_backup_files()),tool_data_size(),database_backup_files())


def prune_snapshots(db: Session, *, map_id: str | None, older_than_days: int, keep_latest: int) -> int:
    if older_than_days < 1: raise ValueError("older_than_days must be >= 1")
    keep_latest=max(1,keep_latest); cutoff=utcnow()-timedelta(days=older_than_days)
    map_ids: Iterable[str] = [map_id] if map_id else db.scalars(select(Snapshot.map_id).distinct()).all()
    deleted=0
    for mid in map_ids:
        snapshots=db.scalars(select(Snapshot).where(Snapshot.map_id==mid).order_by(Snapshot.captured_at.desc(),Snapshot.id.desc())).all()
        keep_ids={s.id for s in snapshots[:keep_latest]}
        for snap in snapshots[keep_latest:]:
            captured=snap.captured_at
            if captured.tzinfo is None:
                from datetime import timezone
                captured=captured.replace(tzinfo=timezone.utc)
            if captured < cutoff and snap.id not in keep_ids: db.delete(snap); deleted+=1
    db.commit(); return deleted


def prune_object_versions(db: Session, *, map_id: str | None, older_than_days: int) -> int:
    if older_than_days < 1: raise ValueError("older_than_days must be >= 1")
    cutoff=utcnow()-timedelta(days=older_than_days); stmt=select(ObjectVersion)
    if map_id: stmt=stmt.where(ObjectVersion.map_id==map_id)
    rows=db.scalars(stmt.order_by(ObjectVersion.map_id,ObjectVersion.object_id,ObjectVersion.id.desc())).all(); seen=set(); deleted=0
    for row in rows:
        key=(row.map_id,row.object_id)
        if key not in seen: seen.add(key); continue
        captured=row.captured_at
        if captured.tzinfo is None:
            from datetime import timezone
            captured=captured.replace(tzinfo=timezone.utc)
        if captured < cutoff: db.delete(row); deleted+=1
    db.commit(); return deleted


def purge_archived_map(db: Session, map_id: str) -> dict[str,int]:
    if db.scalar(select(MapWatch).where(MapWatch.map_id==map_id)) is not None: raise ValueError("Map is still watched")
    counts={"snapshots":db.scalar(select(func.count()).select_from(Snapshot).where(Snapshot.map_id==map_id)) or 0,"versions":db.scalar(select(func.count()).select_from(ObjectVersion).where(ObjectVersion.map_id==map_id)) or 0,"current":db.scalar(select(func.count()).select_from(CurrentObject).where(CurrentObject.map_id==map_id)) or 0}
    db.execute(delete(Snapshot).where(Snapshot.map_id==map_id)); db.execute(delete(ObjectVersion).where(ObjectVersion.map_id==map_id)); db.execute(delete(CurrentObject).where(CurrentObject.map_id==map_id)); db.commit(); return {k:int(v) for k,v in counts.items()}


def vacuum_database() -> None:
    if not settings.database_url.startswith("sqlite"): raise ValueError("VACUUM is only implemented for SQLite")
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        try: conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception: pass
        conn.exec_driver_sql("VACUUM")
