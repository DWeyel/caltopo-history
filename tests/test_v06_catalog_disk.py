# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import AppSetting, Base
from app.services import build_catalog_tree, ensure_backup_disk_space, extract_team_maps
from app.storage_guard import DiskSpaceBlocked, DiskSpaceStatus


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_catalog_resolves_owner_folder_updated_and_same_title_without_merging():
    payload = {
        "features": [
            {"id": "F1", "properties": {"class": "UserFolder", "title": "Operations", "accountId": "TEAM01", "folderId": None}},
            {"id": "F2", "properties": {"class": "UserFolder", "title": "2026", "accountId": "TEAM01", "folderId": "F1"}},
            {"id": "MAPA01", "properties": {"class": "CollaborativeMap", "title": "Example Area", "accountId": "TEAM01", "folderId": "F2", "updated": 1787090000000}},
            {"id": "MAPB02", "properties": {"class": "CollaborativeMap", "title": "Example Area", "accountId": "TEAM01", "folderId": "F1", "updated": 1787080000000}},
        ],
        "accounts": [
            {"id": "TEAM01", "properties": {"class": "UserAccount", "title": "Example Team"}},
        ],
        "rels": [],
    }
    maps = extract_team_maps(payload)
    assert {m["id"] for m in maps} == {"MAPA01", "MAPB02"}
    deep = next(m for m in maps if m["id"] == "MAPA01")
    assert deep["owner_name"] == "Example Team"
    assert deep["folder_path"] == "Operations / 2026"
    assert deep["same_title_count"] == 2
    assert deep["updated_at"] == datetime.fromtimestamp(1787090000, tz=timezone.utc)
    tree = build_catalog_tree(maps)
    assert tree[0]["name"] == "Example Team"
    assert tree[0]["map_count"] == 2
    assert tree[0]["children"][0]["name"] == "Operations"


def test_catalog_deduplicates_repeated_same_map_id_preferring_newest():
    payload = {
        "features": [
            {"id": "MAP001", "properties": {"class": "CollaborativeMap", "title": "Alt", "accountId": "T", "updated": 1000}},
            {"id": "MAP001", "properties": {"class": "CollaborativeMap", "title": "Neu", "accountId": "T", "updated": 2000}},
        ]
    }
    maps = extract_team_maps(payload)
    assert len(maps) == 1
    assert maps[0]["title"] == "Neu"


def test_disk_guard_blocks_backups_below_hard_threshold(monkeypatch):
    db = make_db()
    db.add(AppSetting(key="disk_warning_free_mb", value="4096"))
    db.add(AppSetting(key="disk_hard_free_mb", value="2048"))
    db.commit()

    def fake_status(*, warning_free_mb, hard_free_mb):
        return DiskSpaceStatus(
            path="/var/lib/caltopo-history",
            total_bytes=10 * 1024**3,
            used_bytes=9 * 1024**3,
            free_bytes=1024**3,
            warning_free_bytes=warning_free_mb * 1024**2,
            hard_free_bytes=hard_free_mb * 1024**2,
        )

    monkeypatch.setattr("app.services.disk_space_status", fake_status)
    with pytest.raises(DiskSpaceBlocked) as exc:
        ensure_backup_disk_space(db)
    assert exc.value.free_bytes == 1024**3
    assert exc.value.hard_free_bytes == 2048 * 1024**2
