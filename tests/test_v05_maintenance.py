# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import AuditLog, Base, CurrentObject, MapWatch, ObjectVersion, Snapshot, utcnow
from app.history import pack_json
from app.maintenance import prune_object_versions, prune_snapshots, purge_archived_map, storage_overview
from app.services import add_audit


def feature(oid: str, title: str):
    return {
        "type": "Feature",
        "id": oid,
        "geometry": {"type": "Point", "coordinates": [8, 50]},
        "properties": {"class": "Marker", "title": title},
    }


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_storage_overview_reports_map_and_snapshot_bytes():
    db = make_db()
    blob = pack_json({"type": "FeatureCollection", "features": [feature("1", "A")]})
    db.add(MapWatch(map_id="MAP1", title="Example Map"))
    db.add(Snapshot(map_id="MAP1", state_gz=blob, object_count=1))
    db.add(CurrentObject(map_id="MAP1", object_id="1", object_type="Marker", title="A", feature_gz=pack_json(feature("1", "A")), updated_at=utcnow()))
    db.commit()

    overview = storage_overview(db)
    row = next(x for x in overview.maps if x.map_id == "MAP1")
    assert row.title == "Example Map"
    assert row.snapshot_count == 1
    assert row.snapshot_bytes == len(blob)
    assert row.logical_bytes >= len(blob)
    assert overview.logical_bytes >= row.logical_bytes


def test_snapshot_pruning_keeps_latest_even_if_all_are_old():
    db = make_db()
    old = utcnow() - timedelta(days=200)
    for i in range(5):
        db.add(Snapshot(
            map_id="MAP1",
            captured_at=old + timedelta(minutes=i),
            state_gz=pack_json({"type": "FeatureCollection", "features": [feature(str(i), str(i))]}),
            object_count=1,
        ))
    db.commit()

    deleted = prune_snapshots(db, map_id="MAP1", older_than_days=90, keep_latest=2)
    assert deleted == 3
    remaining = db.query(Snapshot).filter_by(map_id="MAP1").order_by(Snapshot.captured_at).all()
    assert len(remaining) == 2


def test_object_history_pruning_keeps_newest_version_per_object():
    db = make_db()
    old = utcnow() - timedelta(days=365)
    for oid in ("a", "b"):
        for i in range(3):
            db.add(ObjectVersion(
                map_id="MAP1", object_id=oid, object_type="Marker", title=f"{oid}-{i}",
                captured_at=old + timedelta(minutes=i), deleted=False, feature_gz=pack_json(feature(oid, f"{oid}-{i}")),
            ))
    db.commit()

    deleted = prune_object_versions(db, map_id="MAP1", older_than_days=180)
    assert deleted == 4
    rows = db.query(ObjectVersion).filter_by(map_id="MAP1").all()
    assert len(rows) == 2
    assert {row.object_id for row in rows} == {"a", "b"}


def test_archived_map_purge_refuses_currently_watched_map():
    db = make_db()
    db.add(MapWatch(map_id="MAP1", title="Live"))
    db.commit()
    with pytest.raises(ValueError):
        purge_archived_map(db, "MAP1")


def test_archived_map_purge_removes_stored_history():
    db = make_db()
    db.add(Snapshot(map_id="MAP1", state_gz=pack_json({"type": "FeatureCollection", "features": []}), object_count=0))
    db.add(ObjectVersion(map_id="MAP1", object_id="1", object_type="Marker", title="A", feature_gz=pack_json(feature("1", "A"))))
    db.add(CurrentObject(map_id="MAP1", object_id="1", object_type="Marker", title="A", feature_gz=pack_json(feature("1", "A")), updated_at=utcnow()))
    db.commit()
    counts = purge_archived_map(db, "MAP1")
    assert counts == {"snapshots": 1, "versions": 1, "current": 1}
    assert db.query(Snapshot).filter_by(map_id="MAP1").count() == 0
    assert db.query(ObjectVersion).filter_by(map_id="MAP1").count() == 0
    assert db.query(CurrentObject).filter_by(map_id="MAP1").count() == 0


def test_audit_log_supports_object_title():
    db = make_db()
    add_audit(db, "restore_object", map_id="MAP1", object_id="O1", object_title="Bereitstellungsraum", detail="ok")
    db.commit()
    row = db.query(AuditLog).one()
    assert row.object_title == "Bereitstellungsraum"

def test_database_backup_listing_and_safe_delete(tmp_path, monkeypatch):
    import app.maintenance as maintenance

    dbfile = tmp_path / "caltopo-history.db"
    dbfile.write_bytes(b"db")
    managed = tmp_path / "caltopo-history.db.pre-v0.5-20260818.bak"
    managed.write_bytes(b"backup-data")
    unrelated = tmp_path / "other.bak"
    unrelated.write_bytes(b"do-not-touch")
    monkeypatch.setattr(maintenance, "_database_path", lambda: dbfile)

    files = maintenance.database_backup_files()
    assert [f.name for f in files] == [managed.name]
    assert maintenance.tool_data_size() == len(b"db") + len(b"backup-data")
    removed = maintenance.delete_database_backup(managed.name)
    assert removed == len(b"backup-data")
    assert not managed.exists()
    assert unrelated.exists()
