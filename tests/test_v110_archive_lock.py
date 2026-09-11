# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

import app.main as main
import app.services as services
from app.auth import hash_password
from app.db import AppUser, AuditLog, Base, MapWatch, Snapshot, TeamRule
from app.history import pack_json, snapshot_state


def feature(title="Final"):
    return {"type": "Feature", "id": "one", "properties": {"class": "Marker", "title": title},
            "geometry": {"type": "Point", "coordinates": [8, 50]}}


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(main, "SessionLocal", factory)
    monkeypatch.setattr(services, "ensure_backup_disk_space", lambda db: None)
    with factory() as session:
        yield session
    engine.dispose()


def api(monkeypatch, locked=True):
    client = AsyncMock()
    client.get_team.return_value = {"features": [{"id": "MAP", "properties": {
        "class": "CollaborativeMap", "title": "Final map", "accountId": "ARCHIVE", "locked": locked}}]}
    client.get_map.return_value = {"timestamp": 123, "state": {"type": "FeatureCollection", "features": [feature()]}}
    monkeypatch.setattr(services, "caltopo_client", lambda db: client)
    return client


def test_lock_option_defaults_off_and_ownership_change_does_not_pause(db, monkeypatch):
    client = api(monkeypatch)
    watch = asyncio.run(services.ensure_watch(db, "MAP"))
    db.commit()
    asyncio.run(services.refresh_team_catalog(db, "ROOT"))
    assert watch.active
    client.get_map.assert_not_awaited()
    services.set_app_setting(db, services.PAUSE_WHEN_LOCKED_KEY, "true")
    client.get_team.return_value["features"][0]["properties"]["locked"] = False
    asyncio.run(services.refresh_team_catalog(db, "ROOT"))
    assert watch.active
    client.get_map.assert_not_awaited()


@pytest.mark.parametrize("unchanged", [False, True])
def test_lock_takes_final_full_snapshot_once_and_does_not_auto_resume(db, monkeypatch, unchanged):
    client = api(monkeypatch)
    watch = asyncio.run(services.ensure_watch(db, "MAP"))
    services.set_app_setting(db, services.PAUSE_WHEN_LOCKED_KEY, "true")
    db.commit()
    if unchanged:
        asyncio.run(services.backup_watch(db, watch, force_full=True))
    asyncio.run(services.refresh_team_catalog(db, "ROOT"))
    assert not watch.active
    snap = db.scalars(select(Snapshot).order_by(Snapshot.id.desc())).first()
    assert snap.reason == "locked-final-full"
    assert snapshot_state(snap)["features"][0]["properties"]["title"] == "Final"
    assert watch.quiet_snapshot_at is not None
    client.get_map.assert_awaited_with("MAP", 0)
    count = db.query(Snapshot).count()
    asyncio.run(services.refresh_team_catalog(db, "ROOT"))
    client.get_team.return_value["features"][0]["properties"]["locked"] = False
    asyncio.run(services.refresh_team_catalog(db, "ROOT"))
    rule = TeamRule(team_id="ROOT", pattern=".*")
    db.add(rule)
    db.commit()
    asyncio.run(services.discover_rule(db, rule))
    assert not watch.active
    assert db.query(Snapshot).count() == count


@pytest.mark.parametrize("failure", ["network", "malformed", "disk"])
def test_final_backup_failure_keeps_watch_active_for_retry(db, monkeypatch, failure):
    client = api(monkeypatch)
    watch = asyncio.run(services.ensure_watch(db, "MAP"))
    services.set_app_setting(db, services.PAUSE_WHEN_LOCKED_KEY, "true")
    db.commit()
    if failure == "network":
        client.get_map.side_effect = RuntimeError("unavailable")
    elif failure == "malformed":
        client.get_map.return_value = {"error": "missing map"}
    else:
        monkeypatch.setattr(services, "ensure_backup_disk_space", lambda db: (_ for _ in ()).throw(RuntimeError("disk full")))
    asyncio.run(services.refresh_team_catalog(db, "ROOT"))
    assert watch.active
    assert db.query(Snapshot).count() == 0
    assert db.query(AuditLog).filter_by(action="watch_pause_locked_failed").count() == 1
    client.get_map.side_effect = None
    client.get_map.return_value = {"timestamp": 123, "state": {"type": "FeatureCollection", "features": [feature()]}}
    monkeypatch.setattr(services, "ensure_backup_disk_space", lambda db: None)
    asyncio.run(services.refresh_team_catalog(db, "ROOT"))
    assert not watch.active


def test_archive_browse_compare_download_restore_without_enrollment(db, monkeypatch):
    client = api(monkeypatch)
    snaps = [Snapshot(map_id="MAP", reason="test", state_gz=pack_json({"type": "FeatureCollection", "features": [feature(title)]})) for title in ("Old", "New")]
    db.add_all(snaps)
    db.add(AppUser(username="admin", password_hash=hash_password("test-password"), role="admin", active=True))
    db.commit()
    main.app.dependency_overrides[main.get_db] = lambda: db
    try:
        browser = TestClient(main.app)
        assert browser.get("/archives", follow_redirects=False).status_code == 303
        browser.post("/login", data={"username": "admin", "password": "test-password"})
        for path in ("/archives", "/maps/MAP", f"/maps/MAP/compare?snapshot_a={snaps[0].id}&snapshot_b={snaps[1].id}", f"/snapshots/{snaps[0].id}"):
            response = browser.get(path)
            assert response.status_code == 200, response.text
        assert '/maps/MAP/toggle' not in browser.get('/maps/MAP').text
        assert browser.get(f"/snapshots/{snaps[0].id}/geojson").json()["features"][0]["properties"]["title"] == "Old"
        assert db.query(MapWatch).count() == 0
        response = browser.post(f"/snapshots/{snaps[0].id}/restore", data={"confirmation": "RESTORE MAP"})
        assert response.status_code == 200
        client.edit_object.assert_awaited_once()
        assert db.query(MapWatch).count() == 0
        assert db.query(Snapshot).filter(Snapshot.reason.like("pre-restore%")).count() == 1
        assert browser.get("/maps/UNKNOWN").status_code == 404
    finally:
        main.app.dependency_overrides.clear()


def test_setting_persists_and_is_visible(db):
    db.add(AppUser(username="admin", password_hash=hash_password("test-password"), role="admin", active=True))
    db.commit()
    main.app.dependency_overrides[main.get_db] = lambda: db
    try:
        browser = TestClient(main.app)
        browser.post("/login", data={"username": "admin", "password": "test-password"})
        response = browser.post("/settings", data={"global_interval_minutes": 5, "pause_when_locked_value": "true"})
        assert response.status_code == 200
        assert services.pause_when_locked(db)
        assert 'name="pause_when_locked_value"' in response.text
    finally:
        main.app.dependency_overrides.clear()
