# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import AppSetting, Base, CurrentObject, MapWatch, ObjectVersion
from app.history import compare_states, object_overview, pack_json
from app.main import format_localtime
from app.services import extract_team_maps, effective_poll_interval_seconds


def f(oid, title, x=8):
    return {"type": "Feature", "id": oid, "geometry": {"type": "Point", "coordinates": [x, 50]}, "properties": {"class": "Marker", "title": title}}


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_berlin_time_filter_converts_utc_and_shows_zone():
    dt = datetime(2026, 8, 18, 19, 23, 59, tzinfo=timezone.utc)
    assert format_localtime(dt) == "18.08.2026 21:23:59 CEST"


def test_snapshot_compare_added_removed_changed():
    left = {"type": "FeatureCollection", "features": [f("1", "old"), f("2", "removed"), f("4", "same")]}
    right = {"type": "FeatureCollection", "features": [f("1", "new"), f("3", "added"), f("4", "same")]}
    result = compare_states(left, right)
    assert {(x.object_id, x.status) for x in result} == {("1", "changed"), ("2", "removed"), ("3", "added")}


def test_object_overview_keeps_deleted_objects():
    db = make_db()
    live = f("live", "Live")
    db.add(CurrentObject(map_id="MAP1", object_id="live", object_type="Marker", title="Live", feature_gz=pack_json(live), updated_at=datetime(2026, 8, 18, 18, 0, 0)))
    db.add(ObjectVersion(map_id="MAP1", object_id="live", object_type="Marker", title="Live", deleted=False, feature_gz=pack_json(live)))
    db.add(ObjectVersion(map_id="MAP1", object_id="gone", object_type="Marker", title="Gone", deleted=True, feature_gz=None, captured_at=datetime(2026, 8, 18, 18, 30, 0)))
    db.commit()
    rows = {row.object_id: row for row in object_overview(db, "MAP1")}
    assert rows["live"].exists_now is True
    assert rows["gone"].exists_now is False
    assert rows["gone"].title == "Gone"


def test_team_catalog_uses_collaborative_map_title():
    payload = {
        "features": [
            {"id": "MAP123", "properties": {"class": "CollaborativeMap", "title": "Example Map", "accountId": "TEAM01", "sharing": "PRIVATE"}},
            {"id": "PDF1", "properties": {"class": "PDFLink", "title": "Ignore"}},
        ]
    }
    maps = extract_team_maps(payload)
    assert len(maps) == 1
    assert maps[0]["id"] == "MAP123"
    assert maps[0]["title"] == "Example Map"
    assert maps[0]["account_id"] == "TEAM01"
    assert maps[0]["owner_name"] == "TEAM01"
    assert maps[0]["updated"] is None
    assert maps[0]["updated_at"] is None
    assert maps[0]["sharing"] == "PRIVATE"


def test_per_map_interval_overrides_global_setting():
    db = make_db()
    db.add(AppSetting(key="global_poll_interval_seconds", value="300"))
    watch = MapWatch(map_id="MAP1", title="Test", poll_interval_seconds=None)
    db.add(watch)
    db.commit()
    assert effective_poll_interval_seconds(db, watch) == 300
    watch.poll_interval_seconds = 120
    db.commit()
    assert effective_poll_interval_seconds(db, watch) == 120


def test_object_overview_marks_restored_after_delete_and_recreate():
    db = make_db()
    restored = f("obj1", "Restored")
    db.add(CurrentObject(map_id="MAP1", object_id="obj1", object_type="Marker", title="Restored", feature_gz=pack_json(restored), updated_at=datetime(2026, 8, 18, 20, 0, 0)))
    db.add(ObjectVersion(map_id="MAP1", object_id="obj1", object_type="Marker", title="Old", deleted=False, feature_gz=pack_json(f("obj1", "Old")), captured_at=datetime(2026, 8, 18, 18, 0, 0)))
    db.add(ObjectVersion(map_id="MAP1", object_id="obj1", object_type="Marker", title="Old", deleted=True, feature_gz=None, captured_at=datetime(2026, 8, 18, 19, 0, 0)))
    db.add(ObjectVersion(map_id="MAP1", object_id="obj1", object_type="Marker", title="Restored", deleted=False, feature_gz=pack_json(restored), captured_at=datetime(2026, 8, 18, 20, 0, 0)))
    db.commit()
    row = object_overview(db, "MAP1")[0]
    assert row.exists_now is True
    assert row.restored is True
    assert row.status == "restored"
