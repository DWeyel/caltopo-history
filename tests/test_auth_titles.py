# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from app.auth import hash_password, verify_password
from app.history import map_title


def test_password_hash_roundtrip():
    encoded = hash_password("a-long-test-password")
    assert verify_password("a-long-test-password", encoded)
    assert not verify_password("wrong-password", encoded)
    assert "a-long-test-password" not in encoded


def test_map_title_from_metadata():
    assert map_title({"metadata": {"title": "Einsatz Harz"}}, "ABC123") == "Einsatz Harz"


def test_map_title_from_collaborative_map():
    payload = {"features": [{"id": "ABC123", "properties": {"class": "CollaborativeMap", "title": "USAR Test"}}]}
    assert map_title(payload, "ABC123") == "USAR Test"
