# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import asyncio
from datetime import timedelta, timezone

from sqlalchemy import select

from .db import MapWatch, SessionLocal, TeamRule, utcnow
from .services import (
    add_audit,
    configured_team_id,
    discover_rule,
    discovery_interval_seconds,
    effective_poll_interval_seconds,
    maybe_create_quiet_snapshot,
    refresh_team_catalog,
)


async def scheduler_loop(stop: asyncio.Event) -> None:
    last_catalog_scan = None
    while not stop.is_set():
        with SessionLocal() as db:
            rules = db.scalars(select(TeamRule).where(TeamRule.active.is_(True))).all()
            for rule in rules:
                due = rule.last_scan_at is None or utcnow() - _aware(rule.last_scan_at) >= timedelta(seconds=discovery_interval_seconds(db))
                if due:
                    try:
                        await discover_rule(db, rule)
                    except Exception:
                        pass

            team_id = configured_team_id(db)
            catalog_due = last_catalog_scan is None or utcnow() - last_catalog_scan >= timedelta(seconds=discovery_interval_seconds(db))
            if team_id and catalog_due:
                try:
                    await refresh_team_catalog(db, team_id)
                except Exception:
                    # CalTopo decides whether the configured Service Account has sufficient rights.
                    pass
                last_catalog_scan = utcnow()

            all_watches = db.scalars(select(MapWatch)).all()
            now = utcnow()
            for watch in all_watches:
                # The 30-minute closing snapshot is based on the last known state and is independent
                # of the polling interval. It is also allowed for a map that was manually paused.
                try:
                    maybe_create_quiet_snapshot(db, watch)
                except Exception:
                    db.rollback()

                if watch.active and watch.auto_pause_at is not None and now >= _aware(watch.auto_pause_at):
                    watch.active = False
                    add_audit(
                        db,
                        "watch_auto_paused",
                        map_id=watch.map_id,
                        detail="automatic pause after 7 days",
                    )
                    db.commit()
                    continue

                if not watch.active:
                    continue
                interval = effective_poll_interval_seconds(db, watch)
                due = watch.last_poll_at is None or utcnow() - _aware(watch.last_poll_at) >= timedelta(seconds=interval)
                if due:
                    try:
                        from .services import backup_watch
                        await backup_watch(db, watch)
                    except Exception:
                        pass
        try:
            await asyncio.wait_for(stop.wait(), timeout=10)
        except asyncio.TimeoutError:
            pass


def _aware(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
