# Third-Party Notices and License Review

This document records the dependency and map-provider license review performed for CalTopo History v0.9 on 2026-08-19.

CalTopo History itself is licensed under **GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**. Third-party components remain under their own licenses.

## Direct Python dependencies

| Component | Declared license | Role |
|---|---|---|
| FastAPI | MIT | Web application framework |
| Uvicorn | BSD-3-Clause | ASGI server |
| SQLAlchemy | MIT | Database ORM/toolkit |
| HTTPX | BSD-3-Clause | HTTP client used for CalTopo API access |
| Jinja2 | BSD-3-Clause | HTML templating |
| python-multipart | Apache-2.0 | Form/multipart parsing |
| ItsDangerous | BSD-3-Clause | Signed session data support |

The MIT, BSD and Apache-2.0 licenses used by these direct dependencies are compatible with distributing CalTopo History under AGPLv3. Third-party dependency source remains under its original license.

## Significant transitive Python dependencies

The exact resolved dependency graph can vary because `requirements.txt` intentionally specifies compatible version ranges. Common runtime dependencies of the current stack include the following license families:

| Component | License |
|---|---|
| Starlette | BSD-3-Clause |
| Pydantic | MIT |
| Pydantic Core | MIT |
| Annotated Types | MIT |
| Annotated Doc | MIT |
| Typing Inspection | MIT |
| Typing Extensions | PSF-2.0 |
| AnyIO | MIT |
| HTTPcore | BSD-3-Clause |
| certifi | MPL-2.0 |
| idna | BSD-3-Clause |
| h11 | MIT |
| Click | BSD-3-Clause |
| httptools | MIT |
| python-dotenv | BSD-3-Clause |
| PyYAML | MIT |
| uvloop | MIT OR Apache-2.0 |
| watchfiles | MIT |
| websockets | BSD-3-Clause |
| MarkupSafe | BSD-3-Clause |
| greenlet | MIT AND PSF-2.0 |

MPL-2.0 provides a secondary-license mechanism that includes GNU AGPLv3 unless the specific MPL-covered software is marked incompatible with secondary licenses. The current `certifi` dependency is consumed separately and remains under MPL-2.0.

Because dependency versions can change within the declared ranges, maintainers must repeat the license review when changing dependency ranges or preparing a materially new public release. CI includes a conservative runtime-license check that fails when a newly resolved dependency advertises a license family that has not been reviewed.

A prebuilt container image also contains Debian/Python runtime components with their own licenses. If public binary container images are published, an image-level SBOM/license scan should be added to the release process.

## Leaflet

The web UI uses **Leaflet 1.9.4**, licensed under **BSD-2-Clause**, for interactive map previews.

Leaflet is currently loaded from the `unpkg.com` CDN. The official Leaflet Subresource Integrity (SRI) hashes are included in the `<link>` and `<script>` tags so browsers can verify the retrieved CSS and JavaScript.

Leaflet is provider-agnostic and does not provide map imagery itself.

## OpenStreetMap data and community tile service

The default preview basemap uses:

`https://tile.openstreetmap.org/{z}/{x}/{y}.png`

OpenStreetMap data is available under the **Open Data Commons Open Database License (ODbL)**. The application displays visible map attribution linking to the OpenStreetMap copyright/license page.

Use of the community-operated `tile.openstreetmap.org` service is subject to the OpenStreetMap Foundation Tile Usage Policy. In particular:

- it is suitable for normal interactive human viewing under the policy;
- bulk downloading, scraping, prefetching and offline tile generation are not allowed;
- browser caching must not be intentionally bypassed;
- a valid browser Referer must be allowed to reach the tile service;
- the service is best-effort and has no SLA;
- deployments with material traffic or stricter availability/privacy requirements should use another provider or self-host tiles.

CalTopo History does not implement tile prefetching or offline tile downloads. Tiles are requested directly by the user's browser only for the active map preview/snapshot view.

The tile provider is configurable without a software update using:

- `MAP_TILE_URL`
- `MAP_TILE_ATTRIBUTION`
- `MAP_TILE_MAX_ZOOM`

Operators are responsible for complying with the terms and attribution requirements of whichever provider they configure.

### Privacy note

When the default OpenStreetMap community tile service is used, the user's browser connects directly to OpenStreetMap infrastructure. This can disclose the client's IP address, the application page Referer and the tile coordinates being viewed. The CalTopo object payload itself is not sent to the tile provider by CalTopo History, but the requested tile coordinates reveal the approximate map area being viewed.

For sensitive operational environments, use a tile provider and hosting model appropriate to the organization's privacy and availability requirements.

## CalTopo

CalTopo History is an independent integration project. CalTopo and SARTopo are third-party services/trademarks and are not distributed as part of this software. Users are responsible for complying with the terms applicable to their CalTopo account and API access.

## No warranty

Third-party licenses contain their own warranty and liability disclaimers. CalTopo History is likewise provided without warranty under the terms of the AGPL-3.0-only license.
