# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from datetime import datetime, timezone
from pathlib import Path

from app.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, TRANSLATIONS, normalize_language, translate
from app.main import format_localtime


def test_v08_version_and_language_catalog_are_complete():
    assert DEFAULT_LANGUAGE == "en"
    assert SUPPORTED_LANGUAGES == {"en": "English", "de": "Deutsch"}
    assert set(TRANSLATIONS["en"]) == set(TRANSLATIONS["de"])
    assert normalize_language("EN") == "en"
    assert normalize_language("de") == "de"
    assert normalize_language("unknown") == "en"


def test_translation_and_language_specific_date_format():
    assert translate("en", "settings") == "Settings"
    assert translate("de", "settings") == "Einstellungen"
    dt = datetime(2026, 8, 19, 7, 30, 0, tzinfo=timezone.utc)
    assert format_localtime(dt, "en") == "2026-08-19 09:30:00 CEST"
    assert format_localtime(dt, "de") == "19.08.2026 09:30:00 CEST"


def test_templates_use_translation_layer_and_settings_has_language_picker():
    root = Path(__file__).resolve().parents[1]
    settings = (root / "app/templates/settings.html").read_text()
    base = (root / "app/templates/base.html").read_text()
    assert 'name="ui_language"' in settings
    assert "language_options" in settings
    assert '<html lang="{{ language }}">' in base
    for template in (root / "app/templates").glob("*.html"):
        text = template.read_text()
        assert "Einstellungen" not in text
        assert "Benutzerverwaltung" not in text
        assert "Anmeldung fehlgeschlagen" not in text
