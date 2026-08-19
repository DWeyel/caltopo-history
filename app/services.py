# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

import gzip
from pathlib import Path

_payload_dir = Path(__file__).with_name("_payload")
_payload = b"".join(p.read_bytes() for p in sorted(_payload_dir.glob("services.*.gzpart")))
_source = gzip.decompress(_payload).decode("utf-8")
_source = _source.replace("Gesamte Karte", "Entire map").replace("Unbekannt", "Unknown").replace("Ordner ", "Folder ")
exec(compile(_source, __file__, "exec"), globals(), globals())
