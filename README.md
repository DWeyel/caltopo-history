# CalTopo History v0.9

Self-hosted backup, version history, restore and audit web application for collaborative CalTopo maps.

> CalTopo History is an independent project and is not affiliated with or endorsed by CalTopo, LLC. CalTopo and SARTopo are trademarks/services of their respective owners.

## Main features

- Monitor CalTopo maps by Map ID or select multiple maps from the visible team catalog.
- Mirror the visible CalTopo account/folder structure in the map picker and show owner, sharing state and last catalog update time where available.
- Keep same-title maps with different Map IDs separate and de-duplicate repeated occurrences of the same Map ID.
- On-demand map preview using the current CalTopo objects over a configurable basemap.
- Automatically enroll maps using Team ID + regular-expression rules.
- Global backup interval with optional per-map overrides.
- Change-driven compressed snapshots and per-object history; unchanged polls do not create snapshots.
- Detect changes to existing object geometry/properties, not only additions and deletions.
- Create one closing snapshot 30 minutes after the last detected change, then stay quiet until another change occurs.
- Automatically pause a map watch seven days after enrollment; manual reactivation starts a new seven-day window.
- Current-object overview with existence/restored status, last-change timestamp and live title filter.
- Compare any two snapshots and show added, removed and changed objects.
- Restore historical Marker/Shape versions and roll a map back to a selected snapshot for supported object types.
- Restore audit with user, role, client IP, map/object identifiers and object title.
- Multi-user roles: Admin, User and View. The literal `admin` account is protected against deletion, disabling and role changes.
- Settings hub with user management, restore audit and maintenance.
- Storage reporting and maintenance tools, including snapshot pruning and SQLite `VACUUM`.
- Configurable disk-space warning and hard-stop thresholds.
- Responsive phone/tablet layout and light/dark theme.
- English and German UI; fresh installations default to English.
- All UI timestamps use `Europe/Berlin` and show CET/CEST correctly.
- Snapshot GeoJSON download.

## Documentation

- [Feature brief](FEATURE-BRIEF.md)
- [Release notes for v0.9](RELEASE-NOTES-v0.9.md)
- [Third-party notices and license review](THIRD-PARTY-NOTICES.md)
- [Docker deployment](README-DOCKER.md)
- [Native Debian 12 / ISPConfig deployment](README-DEBIAN-ISPConfig.md)

## License

CalTopo History is licensed under the **GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**.

Copyright © 2026 Dennis Weyel.

See [LICENSE](LICENSE) for the project licensing notice and the canonical GNU AGPLv3 terms referenced there.

The web interface exposes the license, no-warranty notice and a **Source code** link. `SOURCE_CODE_URL` must point to the corresponding source for the version actually deployed. This is especially important for modified versions offered to users over a network.

## Third-party components

The current Python runtime dependency stack, Leaflet and the default OpenStreetMap basemap integration were reviewed for v0.9. No blocking license incompatibility was identified in the reviewed stack. Third-party components remain under their own licenses; details and operator obligations are documented in [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

CI includes a conservative runtime dependency-license check so newly resolved license families require review before being accepted.

## Basemap / OpenStreetMap

The map preview defaults to the OpenStreetMap community tile service and displays OpenStreetMap attribution. The tile provider is configurable with:

```text
MAP_TILE_URL
MAP_TILE_ATTRIBUTION
MAP_TILE_MAX_ZOOM
```

The default community tile service is intended for normal interactive viewing, not bulk downloading, scraping, prefetching or offline tile generation. Deployments with significant traffic, strict availability requirements, or sensitive operational use should configure an appropriate provider or self-hosted tile service. See [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

## Language settings

Open **Settings → Backup & CalTopo → Language** and select English or German. Fresh installations default to English.

## Deployment options

### Docker / Docker Compose

See [README-DOCKER.md](README-DOCKER.md).

### Debian 12 + ISPConfig

See [README-DEBIAN-ISPConfig.md](README-DEBIAN-ISPConfig.md).

## CalTopo permissions

- Explicit Map-ID backup: at least READ in the current implementation.
- Restore/write-back requires suitable CalTopo write permission for the affected map objects.
- Team catalog, picker, title synchronization and regex discovery use the permissions actually granted to the configured service account; the application does not hard-code a specific CalTopo role requirement.

## Restore limitation

The application writes only object classes covered by the implemented CalTopo write API paths: `Marker` and `Shape`. Other object classes remain in backup history but are not written back through undocumented endpoints.

## Security note

CalTopo service-account credentials remain server-side. Deploy the application behind HTTPS, use strong application credentials, keep the source-code link correct for the deployed version, and review the privacy implications of any external basemap provider used by browser clients.
