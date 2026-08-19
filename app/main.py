from __future__ import annotations

import gzip
from pathlib import Path

_payload_dir = Path(__file__).with_name("_payload")
_payload = b"".join(p.read_bytes() for p in sorted(_payload_dir.glob("main.*.gzpart")))
exec(compile(gzip.decompress(_payload), __file__, "exec"), globals(), globals())
