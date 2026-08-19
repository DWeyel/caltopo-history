# CalTopo History v0.10 — Release Notes

## Overview

v0.10 focuses on deployment safety and CI reliability. It adds explicit diagnostics for the common Secure-cookie/HTTP login failure, an optional standalone HTTPS deployment with Caddy, and a more robust GitHub Actions status/reporting setup.

## HTTPS and login-session safety

- `COOKIE_SECURE=true` remains the recommended production default.
- When the application is opened over plain HTTP while Secure cookies are enabled, the login page displays a clear warning explaining why login sessions cannot persist.
- Documentation now explicitly states that a browser-facing HTTPS URL is required when `COOKIE_SECURE=true`.
- `COOKIE_SECURE=false` is documented only for temporary trusted local/test HTTP access.

## Optional standalone HTTPS

Docker deployments can now choose between an existing external reverse proxy or the included optional Caddy Compose overlay.

The standalone overlay adds `compose.https.yaml` and `Caddyfile`. With a public DNS name and reachable ports 80/443, Caddy provides automatic HTTPS certificate management and HTTP-to-HTTPS redirection while CalTopo History remains HTTP-only on the internal Docker network.

## CI / GitHub Actions

- Test and container-compliance workflows publish commit statuses linking directly to their Actions run.
- The status bridge makes the run ID discoverable through the connected GitHub API.
- `concurrency` with `cancel-in-progress` cancels superseded runs after rapid successive pushes, reducing duplicate failure notifications.
- GitHub-maintained checkout/setup actions use Node-24-based major versions.
- CI uses a writable temporary SQLite path instead of `/data`.
- Historical feature tests were normalized to test supported behavior rather than old version strings or a hard-coded basemap-provider name.

## Compatibility

v0.10 remains database-compatible with v0.9. Existing monitored maps, snapshots, object histories, users, settings and restore-audit records are retained.
