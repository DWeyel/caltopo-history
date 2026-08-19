# CalTopo History v0.10

Self-hosted backup, version history, restore and audit web application for collaborative CalTopo maps.

> CalTopo History is an independent project and is not affiliated with or endorsed by CalTopo, LLC. CalTopo and SARTopo are trademarks/services of their respective owners.

## Main features

- Monitor selected CalTopo maps and maintain change-aware snapshots plus per-object history.
- Avoid duplicate snapshots when the map state has not changed.
- Create a closing snapshot after the configured quiet period following changes.
- Compare snapshots and identify added, removed and modified objects.
- Restore supported historical objects or roll a map back to a selected snapshot.
- Maintain a restore audit trail with user, role, client IP and object/map context.
- Discover/select maps from the visible Team catalog and preserve CalTopo folder/account structure where available.
- Configurable global/per-map monitoring intervals and automatic watch expiration.
- Multi-user roles: Admin, User and View.
- Storage reporting, retention/maintenance tools and disk-space safety thresholds.
- Responsive UI with light/dark mode.
- English and German UI; fresh installations default to English.
- Configurable map tile provider and on-demand map preview.
- Docker and native Debian/ISPConfig deployment options.
- Optional standalone HTTPS deployment with Caddy.
- SPDX SBOM/container-license scanning and runtime dependency-license CI checks.

## HTTPS / secure-cookie warning

CalTopo History defaults to:

```env
COOKIE_SECURE=true
```

This is the correct production setting, but it **requires the browser-facing URL to use HTTPS**. Browsers do not send Secure cookies over plain HTTP. If the application is opened as `http://...` while `COOKIE_SECURE=true`, valid credentials can be accepted but the login session cannot persist and the browser returns to the login page.

v0.10 displays an explicit warning on the login page when it detects this mismatch.

Use HTTPS for production. Set `COOKIE_SECURE=false` only for a temporary trusted local/test HTTP deployment.

Docker installations can either use an existing reverse proxy or the included optional Caddy overlay. See [Docker deployment](README-DOCKER.md) and [Standalone HTTPS](STANDALONE-HTTPS.md).

## Documentation

- [Feature brief](FEATURE-BRIEF.md)
- [Release notes for v0.10](RELEASE-NOTES-v0.10.md)
- [Docker deployment](README-DOCKER.md)
- [Standalone HTTPS with Caddy](STANDALONE-HTTPS.md)
- [Native Debian 12 / ISPConfig deployment](README-DEBIAN-ISPConfig.md)
- [Third-party notices and license review](THIRD-PARTY-NOTICES.md)
- [Container compliance](CONTAINER-COMPLIANCE.md)

## Language settings

Open **Settings → Backup & CalTopo → Language** and select English or German. Date formatting follows the selected language while retaining the configured `Europe/Berlin` timezone.

## CalTopo permissions

- Explicit Map-ID backup: at least READ in the current implementation.
- Restore/write-back requires suitable CalTopo write permission for the affected map objects.
- Team catalog, picker, title synchronization and regex discovery use the permissions granted to the configured service account; the application does not hard-code a specific CalTopo role requirement.

## Restore limitation

The application writes only object classes covered by the implemented CalTopo write API paths: `Marker` and `Shape`. Other object classes remain in backup history but are not written back through undocumented endpoints.

## License

CalTopo History is licensed under the **GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**.

Copyright © 2026 Dennis Weyel.

See [LICENSE](LICENSE). The web interface exposes the license, no-warranty notice and a configurable source-code link. Operators of modified network deployments should set `SOURCE_CODE_URL` to the Corresponding Source for the version actually running.

## Container compliance

GitHub Actions builds the release-equivalent application image, generates an SPDX JSON SBOM with Syft and creates Trivy container-license reports. The runtime Python dependency-license audit remains a hard CI gate for newly introduced license families. Review the generated artifacts before publishing binary container images.
