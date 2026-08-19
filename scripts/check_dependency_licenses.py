#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only
"""Conservative license-family check for a clean CalTopo History runtime venv.

This is a release guard, not legal advice. It intentionally fails closed when a
new dependency does not advertise a license family we have reviewed.
"""
from __future__ import annotations

import importlib.metadata as md
import sys

IGNORE = {"pip", "setuptools", "wheel"}
APPROVED_MARKERS = (
    "MIT",
    "BSD",
    "Apache",
    "MPL-2.0",
    "Mozilla Public License 2.0",
    "Mozilla Public License 2.0 (MPL 2.0)",
    "PSF-2.0",
    "Python Software Foundation",
    "ISC",
)


def advertised_license(dist: md.Distribution) -> str:
    meta = dist.metadata
    values: list[str] = []
    for key in ("License-Expression", "License"):
        value = meta.get(key)
        if value:
            values.append(value.strip())
    values.extend(
        c.split("::", 2)[-1].strip()
        for c in (meta.get_all("Classifier") or [])
        if c.startswith("License ::")
    )
    # Avoid printing full embedded license texts; first 300 chars are enough for matching/reporting.
    return " | ".join(values)[:300]


def main() -> int:
    failed: list[tuple[str, str, str]] = []
    rows: list[tuple[str, str, str]] = []
    for dist in sorted(md.distributions(), key=lambda d: (d.metadata.get("Name") or "").lower()):
        name = dist.metadata.get("Name") or "unknown"
        if name.lower() in IGNORE:
            continue
        license_text = advertised_license(dist)
        rows.append((name, dist.version, license_text or "UNKNOWN"))
        if not license_text or not any(marker.lower() in license_text.lower() for marker in APPROVED_MARKERS):
            failed.append((name, dist.version, license_text or "UNKNOWN"))

    print("Resolved runtime dependency licenses:")
    for name, version, license_text in rows:
        print(f"- {name} {version}: {license_text}")

    if failed:
        print("\nERROR: dependency license requires manual review:", file=sys.stderr)
        for name, version, license_text in failed:
            print(f"- {name} {version}: {license_text}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
