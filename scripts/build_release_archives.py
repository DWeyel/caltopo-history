#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "app/version.py").read_text().split('APP_VERSION = "', 1)[1].split('"', 1)[0]
OUT = ROOT / "dist"

COMMON = [
    "app", "requirements.txt", "pytest.ini", "LICENSE", "THIRD-PARTY-NOTICES.md",
    "README.md", "FEATURE-BRIEF.md", "CALTOPO-SERVICE-ACCOUNT.md",
    f"RELEASE-NOTES-v{VERSION}.md", "scripts/check_dependency_licenses.py",
]
DOCKER = COMMON + [
    "Dockerfile", "compose.yaml", "compose.https.yaml", "Caddyfile", ".env.example",
    "README-DOCKER.md", "STANDALONE-HTTPS.md", "docker",
]
NATIVE = COMMON + [
    "README-DEBIAN-ISPConfig.md", "deploy",
]


def ignored(path: Path) -> bool:
    return any(part in {"__pycache__", ".pytest_cache", ".venv", ".git"} for part in path.parts) or path.suffix == ".pyc"


def add_path(zf: zipfile.ZipFile, source: Path, arc_root: Path) -> None:
    if source.is_dir():
        for item in sorted(source.rglob("*")):
            if item.is_file() and not ignored(item.relative_to(ROOT)):
                zf.write(item, arc_root / item.relative_to(ROOT))
    elif source.exists() and not ignored(source.relative_to(ROOT)):
        zf.write(source, arc_root / source.relative_to(ROOT))


def build(name: str, members: list[str], folder: str) -> Path:
    OUT.mkdir(exist_ok=True)
    target = OUT / name
    if target.exists():
        target.unlink()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for member in members:
            add_path(zf, ROOT / member, Path(folder))
    return target


def main() -> None:
    docker = build(f"caltopo-history-v{VERSION}-docker.zip", DOCKER, f"caltopo-history-v{VERSION}-docker")
    native = build(f"caltopo-history-debian12-ispconfig-v{VERSION}.zip", NATIVE, f"caltopo-history-debian12-ispconfig-v{VERSION}")
    print(docker)
    print(native)


if __name__ == "__main__":
    main()
