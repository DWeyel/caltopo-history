# CalTopo History 1.1.0

This release adds optional monitoring pauses for locked maps and direct access to archived history.

## Changes

- Added **Settings → Backup & CalTopo → Pause monitoring when a map is locked**. This is off by default and requires a root Team ID with catalog access.
- A catalog check that finds a locked monitored map saves a final full snapshot before pausing. Failed final backups leave monitoring active for retry. Unlocking does not automatically resume monitoring; use Activate after unlocking. Ownership changes alone do not pause a watch.
- Added **Archived maps** navigation and links from Maintenance. Browse snapshots and object history, compare snapshots, download GeoJSON and restore supported objects without re-adding the map to monitoring.
- Restoring archived history no longer creates a watch. A successful pre-restore backup is still required.
- Clarified that rollback operates on Marker/Shape objects within the original existing, unlocked and writable map. It does not recreate a deleted map, restore sharing settings or bypass locks.
- Rollbacks with errors now explicitly report possible partial changes.
- Retained English as the default UI language, matching German translations and existing role permissions.
- Manual releases can create a new version tag after validation. The existing Docker/native archives, SBOM and license-report pipeline is preserved.

## Upgrade

Existing watches, history and settings remain in place. No database schema migration is required. Enable lock-pausing explicitly if it matches your workflow. Keep the persistent data volume and application secret.

Docker images: `ghcr.io/dweyel/caltopo-history:1.1.0` and `ghcr.io/dweyel/caltopo-history:latest`.

## Recovery limits

The CalTopo Team API documents creating new maps, but CalTopo History does not yet implement that separate recovery operation. For a deleted map, download snapshot GeoJSON and import supported objects into a new map in CalTopo, then review the result and configure sharing and monitoring for its new ID. Purged archive data cannot be recovered through the app.

Restore writes can partially succeed. Check the audit before retrying. No live CalTopo map was modified during release testing.
