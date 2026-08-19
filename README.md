# CalTopo History 1.0.1

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
- **Multilingual UI: English and German.** The language is selected globally under Settings.
- **Fresh 1.0.1 installations default to English.** Upgrades from the previous German-only release remain German until changed by an admin.
- All UI timestamps use `Europe/Berlin` and therefore show CET/CEST correctly.
- Snapshot GeoJSON download.
- Explicit HTTP/secure-cookie login diagnostics.
- Optional standalone HTTPS deployment with Caddy and automatic certificate management.

## Language settings

Open **Settings → Backup & CalTopo → Language** and select:

- English
- Deutsch

The setting applies to the full web UI, including login, navigation, forms, status labels, confirmation dialogs, maintenance, restore pages and server-generated flash/error messages handled by the application.

Date formatting follows the selected language while retaining the configured `Europe/Berlin` timezone:

- English: `YYYY-MM-DD HH:MM:SS CET/CEST`
- German: `DD.MM.YYYY HH:MM:SS CET/CEST`


## First-start credentials and application secret

Fresh 1.0.1 installations automatically generate both the internal `APP_SECRET_KEY` and a strong temporary password for the initial `admin` account when explicit values are not supplied. The application secret is persisted and must be kept stable across upgrades. The temporary administrator password is shown during first-start setup and the plaintext handoff file is deleted after the password has been hashed into SQLite. Change the temporary administrator password after the first login.

CalTopo API credentials are separate. They can be supplied through the deployment environment or entered after login under **Settings → Backup & CalTopo → CalTopo connection**. A Credential Secret saved through the UI is encrypted using the installation's `APP_SECRET_KEY` and is never displayed back to the browser.

## Runtime configuration in Settings

Administrators can manage the operational CalTopo connection without editing deployment files:

- CalTopo Credential ID;
- CalTopo Credential Secret (replace-only; never displayed back);
- CalTopo API base URL;
- root Team ID;
- global map backup interval;
- team discovery interval;
- periodic full-map verification cadence;
- UI language and disk-space protection thresholds;
- Secure session-cookie policy (`COOKIE_SECURE`), with immediate runtime effect.

`APP_SECRET_KEY` and the application timezone remain deployment-level settings. `COOKIE_SECURE` can be changed in Settings; a saved UI value overrides the deployment environment until the override is reset.

## Storage / maintenance semantics

Snapshot and map sizes shown in the UI are compressed payload sizes stored in SQLite. The physical SQLite file can be larger because SQLite reuses freed pages internally. Run **Settings → Maintenance → VACUUM** after larger cleanup operations if filesystem space should actually be returned.

Snapshot pruning always retains at least the configured number of newest snapshots per affected map. Object-history pruning retains the newest object version for every object and never deletes the current-object table, so the reconstructed current map state remains intact. Snapshot restores remain possible independently as long as the corresponding snapshot has not been deleted.

Removing a map from monitoring does not delete its stored history. The resulting archive can later be removed explicitly from Maintenance.

## CalTopo service account and permissions

The recommended service-account permission for the full CalTopo History feature set is **WRITE**. In current testing, WRITE is sufficient for backups, team catalog discovery and Marker/Shape restore operations. A READ-only service account can be used for backup-only operation on explicitly configured readable maps, but restore is unavailable and team catalog/discovery may be unavailable.

CalTopo's current API documentation says the team account catalog endpoint requires ADMIN even though current testing shows it working at WRITE. CalTopo History deliberately relies on the permission CalTopo actually grants instead of hard-coding ADMIN. See [`CALTOPO-SERVICE-ACCOUNT.md`](CALTOPO-SERVICE-ACCOUNT.md) for the exact setup steps, the READ-mode behavior matrix and this documentation discrepancy.

## Deployment options

### Docker / Docker Compose

This package includes a complete Docker deployment. It can run behind an existing reverse proxy or use the optional Caddy Compose overlay for standalone automatic HTTPS. See `README-DOCKER.md`.

### Debian 12 + ISPConfig (native)

The native deployment remains included. See `README-DEBIAN-ISPConfig.md`.

## Restore limitation

The application writes only object classes covered by the implemented CalTopo write API paths: `Marker` and `Shape`. Other object classes remain in backup history but are not written back through undocumented endpoints.


## License

CalTopo History is licensed under the **GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**. See [`LICENSE`](LICENSE).

Copyright © 2026 Dennis Weyel.

The web interface includes a source-code link for network users. Operators who deploy a modified version must set `SOURCE_CODE_URL` to a location that provides the Corresponding Source for the version they actually run.

Third-party components remain under their respective licenses; see [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md).

## Map tile provider

The default interactive preview uses the OpenStreetMap community raster tile service. It is intended for modest, user-driven interactive previews only. Do not use it for bulk downloads, offline tile generation, prefetching or high-volume production traffic. The provider is configurable through `MAP_TILE_URL`, `MAP_TILE_ATTRIBUTION` and `MAP_TILE_MAX_ZOOM`. For high-volume, sensitive or operationally critical deployments, configure a suitable commercial or self-hosted provider.

Opening a map preview causes the browser to request map tiles from the configured provider. With the default OpenStreetMap service this discloses the client IP address, HTTP Referer and requested tile coordinates to that third-party service.

## Project status

CalTopo History is an independent project and is not affiliated with or endorsed by CalTopo or SARTopo.


## HTTPS / secure-cookie behavior

CalTopo History 1.0.1 defaults to `COOKIE_SECURE=false`, so a fresh installation can be used over HTTP immediately. This is convenient for local, LAN and reverse-proxy setup before TLS is configured.

For an HTTPS deployment, enable **Settings → Session security → Secure session cookie** (or set `COOKIE_SECURE=true` in the deployment environment before a Settings override exists). When enabled, browsers will send the session cookie only over HTTPS. The Settings change takes effect immediately and can be reset to the deployment-environment value.

HTTPS remains recommended for Internet-facing deployments because `COOKIE_SECURE=false` does not protect the session cookie from being sent over an unencrypted HTTP connection.

## Container compliance

GitHub Actions builds the release-equivalent application image, generates an SPDX JSON SBOM with Syft, and creates full Trivy container-license reports. These artifacts should be reviewed before publishing binary container images. The runtime Python dependency-license audit remains a hard CI gate for newly introduced license families.
