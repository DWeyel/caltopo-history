# CalTopo History 1.1.0

This release adds optional monitoring pauses for locked maps and direct access to archived history.

## Changes

- Added **Settings → Backup & CalTopo → Pause monitoring when a map is locked**. This is off by default and requires a root Team ID with catalog access.
- A catalog check that finds a locked monitored map saves a final full snapshot before pausing. Failed final backups leave monitoring active for retry. Unlocking does not automatically resume monitoring; use Activate after unlocking. Ownership changes alone do not pause a watch.
- Added **Archived maps** navigation and links from Maintenance. Browse snapshots and object history, compare snapshots, download GeoJSON and restore supported objects without re-adding the map to monitoring.
- Restoring archived history no longer creates a watch. A successful pre-restore backup is still required.
- Whole-map recovery can now recreate a deleted CalTopo map through the documented Team API when the backup contains the original owning Team metadata. CalTopo assigns a new Map ID.
- Snapshots now retain the map title, owning Team ID and map properties needed for future deleted-map recovery. Existing-map rollback still requires an unlocked, writable map.
- Rollbacks with errors now explicitly report possible partial changes.
- Retained English as the default UI language, matching German translations and existing role permissions.
- Manual releases can create a new version tag after validation. The existing Docker/native archives, SBOM and license-report pipeline is preserved.

## Upgrade

Existing watches, history and settings remain in place. The SQLite schema is migrated automatically to add nullable map metadata fields for future recovery. Older snapshots remain readable, but a deleted map can only be recreated automatically when its Team metadata is available. Enable lock-pausing explicitly if it matches your workflow. Keep the persistent data volume and application secret.

Docker images: `ghcr.io/dweyel/caltopo-history:1.1.0` and `ghcr.io/dweyel/caltopo-history:latest`.

## Recovery limits

A deleted map is recreated as a new CalTopo map; the original Map ID cannot be restored. Automatic recreation requires recorded owning-Team metadata. Older snapshots without that metadata remain available for GeoJSON download/manual recovery. Existing-map restore writes can partially succeed; locked maps or insufficient UPDATE permission are reported in the restore audit.

No live CalTopo map was modified during release testing.
