from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .config import settings

@dataclass(frozen=True)
class DiskSpaceStatus:
    path: str; total_bytes: int; used_bytes: int; free_bytes: int; warning_free_bytes: int; hard_free_bytes: int
    @property
    def free_percent(self) -> float: return (self.free_bytes / self.total_bytes * 100.0) if self.total_bytes else 0.0
    @property
    def hard_blocked(self) -> bool: return self.free_bytes <= self.hard_free_bytes
    @property
    def warning(self) -> bool: return self.hard_blocked or self.free_bytes <= self.warning_free_bytes

def database_storage_path() -> Path:
    prefix="sqlite:///"
    if settings.database_url.startswith(prefix): return Path(settings.database_url[len(prefix):]).expanduser().resolve().parent
    return Path("/var/lib/caltopo-history")

def disk_space_status(*, warning_free_mb:int, hard_free_mb:int) -> DiskSpaceStatus:
    path=database_storage_path(); path.mkdir(parents=True,exist_ok=True); usage=shutil.disk_usage(path)
    return DiskSpaceStatus(str(path),int(usage.total),int(usage.used),int(usage.free),max(0,int(warning_free_mb))*1024*1024,max(0,int(hard_free_mb))*1024*1024)

class DiskSpaceBlocked(RuntimeError):
    def __init__(self, free_bytes:int, hard_free_bytes:int):
        self.free_bytes=int(free_bytes); self.hard_free_bytes=int(hard_free_bytes); super().__init__("disk_space_hard_limit")
