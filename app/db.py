from __future__ import annotations

import gzip
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, create_engine, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .auth import hash_password
from .config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def auto_pause_default() -> datetime:
    return utcnow() + timedelta(days=7)


class MapWatch(Base):
    __tablename__ = "map_watches"

    id: Mapped[int] = mapped_column(primary_key=True)
    map_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    source: Mapped[str] = mapped_column(String(32), default="manual")
    source_rule_id: Mapped[int | None] = mapped_column(ForeignKey("team_rules.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    poll_interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_server_ts: Mapped[int] = mapped_column(Integer, default=0)
    poll_count: Mapped[int] = mapped_column(Integer, default=0)
    last_poll_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_change_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quiet_snapshot_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_pause_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=auto_pause_default)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TeamRule(Base):
    __tablename__ = "team_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[str] = mapped_column(String(32), index=True)
    pattern: Mapped[str] = mapped_column(String(300))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_server_ts: Mapped[int] = mapped_column(Integer, default=0)
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    map_id: Mapped[str] = mapped_column(String(32), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    server_timestamp: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str] = mapped_column(String(80), default="scheduled")
    object_count: Mapped[int] = mapped_column(Integer, default=0)
    state_gz: Mapped[bytes] = mapped_column(LargeBinary)


class CurrentObject(Base):
    __tablename__ = "current_objects"

    id: Mapped[int] = mapped_column(primary_key=True)
    map_id: Mapped[str] = mapped_column(String(32), index=True)
    object_id: Mapped[str] = mapped_column(String(128), index=True)
    object_type: Mapped[str] = mapped_column(String(80), default="Unknown")
    title: Mapped[str] = mapped_column(String(500), default="")
    feature_gz: Mapped[bytes] = mapped_column(LargeBinary)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = ({"sqlite_autoincrement": True},)


class ObjectVersion(Base):
    __tablename__ = "object_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    map_id: Mapped[str] = mapped_column(String(32), index=True)
    object_id: Mapped[str] = mapped_column(String(128), index=True)
    object_type: Mapped[str] = mapped_column(String(80), default="Unknown")
    title: Mapped[str] = mapped_column(String(500), default="")
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    server_timestamp: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    feature_gz: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    map_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    object_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    actor_username: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    actor_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(80), nullable=True)
    object_title: Mapped[str | None] = mapped_column(String(500), nullable=True)


class AppUser(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(500))
    role: Mapped[str] = mapped_column(String(20), default="view", index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


def _sqlite_migrate() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    with engine.begin() as conn:
        if "audit_log" in table_names:
            columns = {column["name"] for column in inspector.get_columns("audit_log")}
            additions = {
                "actor_username": "VARCHAR(120)",
                "actor_role": "VARCHAR(20)",
                "client_ip": "VARCHAR(80)",
                "object_title": "VARCHAR(500)",
            }
            for name, sql_type in additions.items():
                if name not in columns:
                    conn.execute(text(f"ALTER TABLE audit_log ADD COLUMN {name} {sql_type}"))
            if "object_versions" in table_names:
                conn.execute(text(
                    "UPDATE audit_log SET object_title = ("
                    "SELECT ov.title FROM object_versions ov "
                    "WHERE ov.map_id = audit_log.map_id AND ov.object_id = audit_log.object_id "
                    "ORDER BY ov.id DESC LIMIT 1"
                    ") WHERE object_id IS NOT NULL AND (object_title IS NULL OR object_title = '')"
                ))

        if "map_watches" in table_names:
            columns = {column["name"] for column in inspector.get_columns("map_watches")}
            additions = {
                "poll_interval_seconds": "INTEGER",
                "last_change_at": "DATETIME",
                "quiet_snapshot_at": "DATETIME",
                "auto_pause_at": "DATETIME",
            }
            for name, sql_type in additions.items():
                if name not in columns:
                    conn.execute(text(f"ALTER TABLE map_watches ADD COLUMN {name} {sql_type}"))
            conn.execute(text("UPDATE map_watches SET title = '' WHERE title = map_id"))
            conn.execute(text(
                "UPDATE map_watches SET auto_pause_at = datetime(created_at, '+7 days') "
                "WHERE auto_pause_at IS NULL"
            ))


def _bootstrap_admin() -> None:
    with SessionLocal() as db:
        if db.query(AppUser).count() == 0:
            db.add(AppUser(
                username=settings.app_username,
                password_hash=hash_password(settings.app_password),
                role="admin",
                active=True,
            ))
            db.commit()


def _bootstrap_settings(default_language: str = "en") -> None:
    defaults = {
        "global_poll_interval_seconds": str(max(settings.poll_interval_seconds, 60)),
        "caltopo_team_id": "",
        "disk_warning_free_mb": "4096",
        "disk_hard_free_mb": "2048",
        "ui_language": default_language,
    }
    with SessionLocal() as db:
        changed = False
        for key, value in defaults.items():
            if db.get(AppSetting, key) is None:
                db.add(AppSetting(key=key, value=value))
                changed = True
        if changed:
            db.commit()


def _canonical_snapshot(blob: bytes) -> str:
    value = json.loads(gzip.decompress(blob).decode("utf-8"))
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _cleanup_duplicate_snapshots_once() -> None:
    marker = "snapshot_dedupe_v04_done"
    with SessionLocal() as db:
        if db.get(AppSetting, marker) is not None:
            return
        map_ids = db.scalars(select(Snapshot.map_id).distinct()).all()
        removed = 0
        for map_id in map_ids:
            snapshots = db.scalars(
                select(Snapshot).where(Snapshot.map_id == map_id).order_by(Snapshot.captured_at, Snapshot.id)
            ).all()
            previous_state: str | None = None
            for snap in snapshots:
                try:
                    state = _canonical_snapshot(snap.state_gz)
                except Exception:
                    previous_state = None
                    continue
                if previous_state is not None and state == previous_state:
                    db.delete(snap)
                    removed += 1
                else:
                    previous_state = state
        db.add(AppSetting(key=marker, value=str(removed)))
        db.commit()


def init_db() -> None:
    existing_tables = set(inspect(engine).get_table_names())
    existing_installation = "app_settings" in existing_tables
    Base.metadata.create_all(bind=engine)
    _sqlite_migrate()
    Base.metadata.create_all(bind=engine)
    _bootstrap_admin()
    _bootstrap_settings(default_language="de" if existing_installation else "en")
    _cleanup_duplicate_snapshots_once()
