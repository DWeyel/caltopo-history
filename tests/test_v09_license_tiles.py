# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from pathlib import Path

from app.config import settings


def test_v09_license_and_source_link_are_exposed():
    root = Path(__file__).resolve().parents[1]
    base = (root / "app/templates/base.html").read_text()
    readme = (root / "README.md").read_text()
    license_text = (root / "LICENSE").read_text()
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in license_text
    assert "AGPL-3.0-only" in base
    assert "settings.source_code_url" in base
    assert "AGPL-3.0-only" in readme


def test_v09_tile_provider_is_configurable_and_attributed():
    root = Path(__file__).resolve().parents[1]
    picker = (root / "app/templates/map_picker.html").read_text()
    snapshot = (root / "app/templates/snapshot.html").read_text()
    assert settings.map_tile_url.startswith("https://tile.openstreetmap.org/")
    assert "openstreetmap.org/copyright" in settings.map_tile_attribution
    assert "settings.map_tile_url" in picker
    assert "settings.map_tile_attribution" in picker
    assert "settings.map_tile_url" in snapshot
    assert "settings.map_tile_attribution" in snapshot
    assert "sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" in picker
    assert "sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" in picker
