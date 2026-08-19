# CalTopo History v0.10 — Release Notes

## Overview

v0.10 focuses on deployment safety and CI reliability. It adds explicit diagnostics for the common Secure-cookie/HTTP login failure, an optional standalone HTTPS deployment with Caddy, and a more robust GitHub Actions status/reporting setup.

## HTTPS and login-session safety

- `COOKIE_SECURE=true` remains the recommended production default.
- When a user opens the application over plain HTTP while Secure cookies are enabled, the login page now displays a clear warning.
- Documentation now explicitly explains that a browser-facing HTTPS URL is required when `COOKIE_SECURE=true`.
- `COOKIE_SECURE=false` is documented only for temporary trusted local/test HTTP access.

## Optional standalone HTTPS

Docker deployments can now choose between:

1. an existing external reverse proxy, as before; or
2. the included optional Caddy Compose overlay.

The standalone overlay adds `compose.https.yaml` and `Caddyfile`. With a public DNS name and reachable ports 80/443, Caddy provides automatic HTTPS certificate management and HTTP-to-HTTPS redirection while CalTopo History remains HTTP-only on the internal Docker network.

## CI / GitHub Actions

- Test and container-compliance workflows publish commit statuses that link directly to their Actions run.
- This status bridge makes the run ID discoverable through the connected GitHub API.
- `concurrency` with `cancel-in-progress` cancels superseded runs after rapid successive pushes, reducing duplicate failure notifications.
- GitHub-maintained checkout/setup actions are updated to Node-24-based major versions.
- CI uses a writable temporary SQLite path instead of `/data`.
- Historical feature tests were normalized so they test supported contracts rather than old version strings or hard-coded basemap-provider text.

## Compatibility

v0.10 remains database-compatible with v0.9. Existing maps, snapshots, object histories, users, settings, audit records and language settings are retained.
