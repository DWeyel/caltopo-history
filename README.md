# CalTopo History v0.8

Self-hosted backup, history and restore web application for CalTopo Teams.

## Main features

- Monitor CalTopo maps by Map ID or select multiple maps from the visible team catalog.
- Mirror the visible CalTopo account/folder structure in the map picker and show owner, sharing state and last catalog update time where available.
- Keep same-title maps with different Map IDs separate and de-duplicate repeated occurrences of the same Map ID.
- On-demand map preview in the team catalog using the current CalTopo objects on an OpenStreetMap basemap.
- Automatically enroll maps using Team ID + regular-expression rules.
- Global backup interval with optional per-map overrides.
- Change-driven compressed snapshots and per-object history. Unchanged polls do not create snapshots.
- Detect changes to existing object geometry/properties, not only object additions/deletions.
- Create one closing snapshot 30 minutes after the last detected change, then stay quiet until another change occurs.
- Automatically pause a map watch seven days after enrollment; manual reactivation starts a new seven-day window.
- Current-object overview with existence/restored status, last-change timestamp and live title filter.
- Compare any two snapshots and show added, removed and changed objects.
- Restore historical Marker/Shape versions and roll a map back to a selected snapshot for supported object types.
- Restore audit with user, role, client IP, map/object identifiers and object title.
- Multi-user roles: Admin, User and View. The literal `admin` account is protected against deletion, disabling and role changes.
- Settings hub with user management, restore audit and maintenance.
- Storage reporting for snapshots, per-map archives, object history, current state, SQLite files, upgrade backups and overall tool data.
- Maintenance for pruning old snapshots/object versions, deleting archived map history, deleting updater backups and running SQLite `VACUUM`.
- Configurable disk-space warning and hard-stop thresholds. Backup writes resume automatically after free space recovers.
- Responsive phone/tablet layout.
- Light/dark theme toggle stored in the browser.
- **Multilingual UI (v0.8): English and German.** The language is selected globally under Settings.
- **Fresh v0.8 installations default to English.** Upgrades from the previous German-only release remain German until changed by an admin.
- All UI timestamps use `Europe/Berlin` and therefore show CET/CEST correctly.
- Snapshot GeoJSON download.

## Documentation

- [Feature brief](FEATURE-BRIEF.md)
- [Release notes for v0.8](RELEASE-NOTES-v0.8.md)
- [Docker deployment](README-DOCKER.md)
- [Native Debian 12 / ISPConfig deployment](README-DEBIAN-ISPConfig.md)

## Language settings

Open **Settings → Backup & CalTopo → Language** and select English or German.

The setting applies to the full web UI, including login, navigation, forms, status labels, confirmation dialogs, maintenance, restore pages and server-generated application messages.

Date formatting follows the selected language while retaining the configured `Europe/Berlin` timezone:

- English: `YYYY-MM-DD HH:MM:SS CET/CEST`
- German: `DD.MM.YYYY HH:MM:SS CET/CEST`

## Storage / maintenance semantics

Snapshot and map sizes shown in the UI are compressed payload sizes stored in SQLite. The physical SQLite file can be larger because SQLite reuses freed pages internally. Run **Settings → Maintenance → VACUUM** after larger cleanup operations if filesystem space should actually be returned.

Snapshot pruning always retains at least the configured number of newest snapshots per affected map. Object-history pruning retains the newest object version for every object and never deletes the current-object table, so the reconstructed current map state remains intact. Snapshot restores remain possible independently as long as the corresponding snapshot has not been deleted.

Removing a map from monitoring does not delete its stored history. The resulting archive can later be removed explicitly from Maintenance.

## CalTopo permissions

- Explicit Map-ID backup: at least READ in the current implementation.
- Restore/write-back requires suitable CalTopo write permission for the affected map objects.
- Team catalog, picker, title synchronization and regex discovery use the permissions actually granted to the configured service account. The application does not hard-code a specific CalTopo role requirement.

## Deployment options

### Docker / Docker Compose

This package includes a complete Docker deployment. See `README-DOCKER.md`.

### Debian 12 + ISPConfig (native)

The native deployment remains included. See `README-DEBIAN-ISPConfig.md`.

## Restore limitation

The application writes only object classes covered by the implemented CalTopo write API paths: `Marker` and `Shape`. Other object classes remain in backup history but are not written back through undocumented endpoints.
