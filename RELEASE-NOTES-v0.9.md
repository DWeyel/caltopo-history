# CalTopo History v0.9 — Release Notes

## Overview

v0.9 prepares CalTopo History for an eventual public open-source release. It does not change the core backup and restore model introduced in earlier versions; the focus is licensing, source availability, dependency transparency and safer third-party map integration.

## Licensing

- CalTopo History is now licensed under **GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**.
- The full license text is included as `LICENSE`.
- Copyright notice: **© 2026 Dennis Weyel**.
- The web interface now displays the license, no-warranty notice and a **Source code** link.
- `SOURCE_CODE_URL` is configurable so operators of modified AGPL deployments can point users to the Corresponding Source for the version actually running.
- Docker image metadata declares `AGPL-3.0-only` and the upstream source repository.

## Third-party license review

A dependency/license review was completed for the direct Python dependencies, common transitive runtime dependencies, Leaflet and the default OpenStreetMap basemap. Results are documented in `THIRD-PARTY-NOTICES.md`.

No blocking license incompatibility was identified for the current application stack. The reviewed dependencies use permissive MIT/BSD/Apache licenses, MPL-2.0, PSF licensing, or compatible combinations.

## OpenStreetMap tile-service compliance

The map-preview integration was adjusted to better match the OpenStreetMap Foundation Tile Usage Policy:

- visible OpenStreetMap attribution links to the OpenStreetMap copyright/license page;
- the tile URL is no longer an application constant and can be changed through configuration;
- tile attribution and maximum zoom are configurable;
- no prefetch/offline tile behavior is implemented;
- documentation explains the no-SLA and privacy implications of the community tile service.

New configuration variables:

- `MAP_TILE_URL`
- `MAP_TILE_ATTRIBUTION`
- `MAP_TILE_MAX_ZOOM`

## Leaflet CDN integrity

Leaflet remains at version 1.9.4. The official Subresource Integrity hashes are now applied to the Leaflet CSS and JavaScript CDN references.

## Public source-tree cleanup

The GitHub repository is stored as a normal browsable source tree in v0.9. Python modules, templates, stylesheets, tests and deployment scripts are directly visible rather than hidden behind transport-specific compressed support payloads.

## Compatibility

v0.9 is database-compatible with v0.8. Existing monitored maps, snapshots, object histories, users, settings and restore-audit records are retained.
