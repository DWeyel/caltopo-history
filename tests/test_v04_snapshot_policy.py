# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

import asyncio
from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, CurrentObject, MapWatch, Snapshot, utcnow
from app.history import create_snapshot_if_changed, pack_json
from app.services import ensure_watch, maybe_create_quiet_snapshot


def feature(title="A"):
    return {"type": "Feature", "id": "1", "geometry": {"type": "Point", "coordinates": [8, 50]}, "properties": {"class": "Marker", "title": title}}


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_snapshots_are_only_created_when_state_changes():
    db = make_db()
    db.add(CurrentObject(map_id="MAP", object_id="1", object_type="Marker", title="A", feature_gz=pack_json(feature("A")), updated_at=utcnow()))
    db.commit()
    first = create_snapshot_if_changed(db, "MAP", 1, "initial")
    assert first is not None
    db.commit()
    assert create_snapshot_if_changed(db, "MAP", 2, "scheduled") is None

    row = db.query(CurrentObject).filter_by(map_id="MAP", object_id="1").one()
    row.title = "B"
    row.feature_gz = pack_json(feature("B"))
    db.commit()
    changed = create_snapshot_if_changed(db, "MAP", 3, "scheduled")
    assert changed is not None
    db.commit()
    assert db.query(Snapshot).filter_by(map_id="MAP").count() == 2


def test_quiet_snapshot_is_created_once_after_30_minutes():
    db = make_db()
    db.add(CurrentObject(map_id="MAP", object_id="1", object_type="Marker", title="A", feature_gz=pack_json(feature("A")), updated_at=utcnow()))
    watch = MapWatch(map_id="MAP", active=True, last_server_ts=123, last_change_at=utcnow() - timedelta(minutes=31))
    db.add(watch)
    db.commit()
    create_snapshot_if_changed(db, "MAP", 123, "change")
    db.commit()

    quiet = maybe_create_quiet_snapshot(db, watch)
    assert quiet is not None
    assert quiet.reason == "30min-after-last-change"
    assert maybe_create_quiet_snapshot(db, watch) is None
    assert db.query(Snapshot).filter_by(map_id="MAP").count() == 2


def test_pattern_discovery_does_not_reactivate_paused_watch_but_manual_reactivation_does():
    db = make_db()
    watch = MapWatch(map_id="MAP", active=False, auto_pause_at=utcnow() - timedelta(days=1))
    db.add(watch)
    db.commit()

    same = asyncio.run(ensure_watch(db, "MAP", source="pattern", title="Name", reactivate=False))
    assert same.active is False

    same = asyncio.run(ensure_watch(db, "MAP", source="manual", title="Name", reactivate=True))
    assert same.active is True
    assert same.auto_pause_at > utcnow() + timedelta(days=6, hours=23)
