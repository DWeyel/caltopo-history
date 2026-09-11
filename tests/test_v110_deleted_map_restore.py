# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.services as services
from app.caltopo import CalTopoError
from app.db import AuditLog, Base, MapWatch, Snapshot
from app.history import pack_json


def marker(title="Old"):
    return {
        "type": "Feature",
        "id": "M1",
        "geometry": {"type": "Point", "coordinates": [8.0, 50.0]},
        "properties": {"class": "Marker", "title": title},
    }


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(services, "ensure_backup_disk_space", lambda db: None)
    with factory() as session:
        yield session
    engine.dispose()


def test_deleted_map_is_recreated_with_new_id_and_metadata(db, monkeypatch):
    watch = MapWatch(
        map_id="OLDMAP",
        title="Incident map",
        team_id="TEAM01",
        map_properties_gz=pack_json({
            "title": "Incident map",
            "accountId": "TEAM01",
            "mode": "sar",
            "sharing": "SECRET",
            "config": '{"activeLayers":[["mbt",1]]}',
            "class": "CollaborativeMap",
        }),
        active=True,
    )
    snap = Snapshot(
        map_id="OLDMAP",
        map_title="Incident map",
        team_id="TEAM01",
        map_properties_gz=watch.map_properties_gz,
        reason="test",
        state_gz=pack_json({"type": "FeatureCollection", "features": [marker()]}),
    )
    db.add_all([watch, snap])
    db.commit()

    client = AsyncMock()
    client.get_map.side_effect = CalTopoError("CalTopo API 404: missing", status_code=404, response_text="missing")
    client.create_map.return_value = {"id": "NEWMAP"}
    monkeypatch.setattr(services, "caltopo_client", lambda db: client)

    stats = asyncio.run(services.restore_snapshot(db, snap, actor_username="admin", actor_role="admin", client_ip="127.0.0.1"))

    assert stats["recreated_map"] == 1
    assert stats["new_map_id"] == "NEWMAP"
    assert stats["restored"] == 1
    client.create_map.assert_awaited_once()
    team_id, payload = client.create_map.await_args.args
    assert team_id == "TEAM01"
    assert payload["properties"]["title"] == "Incident map"
    assert payload["properties"]["mode"] == "sar"
    assert payload["properties"]["sharing"] == "SECRET"
    assert payload["properties"]["mapConfig"] == '{"activeLayers":[["mbt",1]]}'
    assert payload["state"]["features"][0].get("id") is None
    assert "class" not in payload["state"]["features"][0]["properties"]

    assert not watch.active
    replacement = db.scalar(select(MapWatch).where(MapWatch.map_id == "NEWMAP"))
    assert replacement is not None and replacement.active
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "restore_snapshot_recreated_map"))
    assert audit is not None and "new_map_id=NEWMAP" in audit.detail


def test_deleted_map_without_team_metadata_fails_without_creating_map(db, monkeypatch):
    snap = Snapshot(
        map_id="OLDMAP",
        reason="legacy",
        state_gz=pack_json({"type": "FeatureCollection", "features": [marker()]}),
    )
    db.add(snap)
    db.commit()

    client = AsyncMock()
    client.get_map.side_effect = CalTopoError("CalTopo API 404: missing", status_code=404)
    monkeypatch.setattr(services, "caltopo_client", lambda db: client)

    with pytest.raises(ValueError, match="Team ID was not recorded"):
        asyncio.run(services.restore_snapshot(db, snap))
    client.create_map.assert_not_awaited()


def test_existing_locked_or_unwritable_map_records_api_error_detail(db, monkeypatch):
    snap = Snapshot(
        map_id="MAP",
        reason="test",
        state_gz=pack_json({"type": "FeatureCollection", "features": [marker("Target")]}),
    )
    db.add(snap)
    db.commit()

    client = AsyncMock()
    client.get_map.return_value = {
        "timestamp": 100,
        "state": {"type": "FeatureCollection", "features": [marker("Current")]},
    }
    client.edit_object.side_effect = CalTopoError(
        "CalTopo API 403: map is locked", status_code=403, response_text="map is locked"
    )
    monkeypatch.setattr(services, "caltopo_client", lambda db: client)
    monkeypatch.setattr(services, "pre_restore_snapshot", AsyncMock(return_value=None))

    stats = asyncio.run(services.restore_snapshot(db, snap, actor_username="admin"))
    assert stats["errors"] == 1
    assert any("403" in item and "locked" in item for item in stats["error_details"])
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "restore_snapshot"))
    assert audit is not None
    assert "map is locked" in audit.detail
