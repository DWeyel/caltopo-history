# CalTopo History v0.9 — Release Notes

## Overview

v0.9 prepares CalTopo History for an eventual public open-source release. It does not change the core backup and restore model introduced in earlier versions; the focus is licensing, source availability, dependency transparency, container compliance and safer third-party map integration.

## Licensing

- CalTopo History is now licensed under **GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**.
- Copyright notice: **© 2026 Dennis Weyel**.
- Release distributions include a verbatim copy of the GNU AGPLv3 license text.
- The web interface displays the license, no-warranty notice and a **Source code** link.
- `SOURCE_CODE_URL` is configurable so operators of modified AGPL deployments can point users to the Corresponding Source for the version actually running.
- Docker image metadata declares `AGPL-3.0-only` and the upstream source repository.

## Third-party license review

A dependency/license review was completed for the direct Python dependencies, common transitive runtime dependencies, Leaflet and the default OpenStreetMap basemap. Results are documented in `THIRD-PARTY-NOTICES.md`.

No blocking license incompatibility was identified for the reviewed application stack. Third-party components remain under their own licenses.

A conservative CI license guard was added. Runtime dependencies are resolved in a clean environment and the build fails when a previously unreviewed license family appears.

## Container SBOM and license scan

A new **Container compliance** GitHub Actions workflow provides a release-oriented compliance view of the complete built Docker image.

The workflow:

- builds the current container image from the repository;
- generates an SPDX JSON SBOM with Anchore Syft;
- performs a full container license scan with Aqua Security Trivy;
- uploads machine-readable and human-readable license reports as workflow artifacts;
- can be triggered automatically by relevant image/source changes or manually.

The Trivy container license report is intentionally review-oriented. Trivy's risk classification is useful for identifying licenses that require attention, but it is not treated as an automatic legal compatibility decision for Debian operating-system packages. The existing application dependency-license guard remains the hard CI gate for newly introduced/unreviewed Python runtime license families.

The public-image release checklist is documented in `CONTAINER-COMPLIANCE.md`.

## OpenStreetMap tile-service compliance

The map-preview integration was adjusted to better support compliant operation with the OpenStreetMap community tile service or an alternative provider:

- visible OpenStreetMap attribution links to the OpenStreetMap copyright/license page;
- tile URL, attribution and maximum zoom are configurable;
- no tile prefetching or offline download behavior is implemented;
- documentation covers service limitations and privacy considerations.

New configuration variables:

- `MAP_TILE_URL`
- `MAP_TILE_ATTRIBUTION`
- `MAP_TILE_MAX_ZOOM`

## Leaflet CDN integrity

Leaflet remains at version 1.9.4. The official Subresource Integrity hashes are applied to the Leaflet CSS and JavaScript CDN references.

## Source availability

The application footer exposes a configurable **Source code** link together with the AGPL license and no-warranty notice. Operators who deploy a modified version should configure `SOURCE_CODE_URL` to the Corresponding Source for the version actually offered to network users.

## Compatibility

v0.9 is database-compatible with v0.8. Existing monitored maps, snapshots, object histories, users, settings and restore-audit records are retained.
