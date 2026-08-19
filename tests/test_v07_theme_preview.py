# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

import asyncio
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.main import map_picker_preview


class FakeCalTopoClient:
    async def get_map(self, map_id: str, since: int = 0):
        assert map_id == "ABC123"
        assert since == 0
        return {
            "timestamp": 123,
            "features": [
                {
                    "id": "M1",
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [8.7, 50.1]},
                    "properties": {"class": "Marker", "title": "Testmarker"},
                }
            ],
        }


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_picker_preview_returns_live_geojson(monkeypatch):
    db = make_db()
    monkeypatch.setattr("app.main.caltopo_client", lambda db: FakeCalTopoClient())
    result = asyncio.run(map_picker_preview("ABC123", db))
    assert result["ok"] is True
    assert result["source"] == "live"
    assert result["state"]["type"] == "FeatureCollection"
    assert result["state"]["features"][0]["properties"]["title"] == "Testmarker"


def test_templates_contain_darkmode_and_lazy_preview_controls():
    root = Path(__file__).resolve().parents[1]
    base = (root / "app/templates/base.html").read_text()
    picker = (root / "app/templates/map_picker.html").read_text()
    css = (root / "app/static/app.css").read_text()
    assert "caltopo-theme" in base
    assert 'id="theme-toggle"' in base
    assert "data-theme=\"dark\"" in css
    assert "preview-toggle" in picker
    assert "/api/maps/${encodeURIComponent(mapId)}/preview" in picker
    assert "settings.map_tile_url" in picker
    assert "settings.map_tile_attribution" in picker
