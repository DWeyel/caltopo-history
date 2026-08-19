# CalTopo History v0.10 — Docker deployment

## Included

- application source (`app/`)
- `Dockerfile`
- `compose.yaml`
- optional standalone HTTPS overlay (`compose.https.yaml`, `Caddyfile`)
- `.env.example`
- persistent SQLite volume
- container healthcheck
- non-root application runtime
- database backup/import/export helpers
- Apache/Nginx reverse-proxy examples

## Requirements

- Docker Engine with Compose v2
- Internet access during image build
- CalTopo Team service-account credentials

## Fresh installation

```bash
unzip caltopo-history-v0.10-docker.zip
cd caltopo-history-docker-v0.10
cp .env.example .env
nano .env
```

Set at least:

```env
CALTOPO_CREDENTIAL_ID=...
CALTOPO_CREDENTIAL_SECRET=...
APP_PASSWORD=...
APP_SECRET_KEY=...
COOKIE_SECURE=true
```

Generate an application secret, for example:

```bash
openssl rand -hex 48
```

### Existing reverse proxy

Start the application normally:

```bash
docker compose up -d --build
```

The default host binding is `127.0.0.1:8765`. Put Apache, Nginx, Caddy, Traefik or another TLS reverse proxy in front of it.

### Standalone automatic HTTPS

Set a public domain in `.env`:

```env
DOMAIN=history.example.org
COOKIE_SECURE=true
```

DNS must point to the Docker host and ports 80/tcp and 443/tcp must be reachable. Then start:

```bash
docker compose -f compose.yaml -f compose.https.yaml up -d --build
```

Caddy obtains and renews the public TLS certificate and redirects HTTP to HTTPS. CalTopo History itself remains HTTP-only on the internal Docker network. See [STANDALONE-HTTPS.md](STANDALONE-HTTPS.md).

## HTTPS and login cookies — important

**Production deployments must use HTTPS.** The default is:

```env
COOKIE_SECURE=true
```

This marks the login session cookie as `Secure`. Browsers **do not send Secure cookies over plain HTTP**. **Login sessions cannot work over plain HTTP when `COOKIE_SECURE=true`.**

If you open CalTopo History as `http://host:8765`, the username/password can be correct but the login session cannot persist and you will be sent back to the login page. v0.10 shows an explicit warning on the login page when it detects this configuration mismatch.

For a temporary trusted local HTTP-only test you may use:

```env
COOKIE_SECURE=false
```

**Do not use `COOKIE_SECURE=false` for an Internet-facing deployment.**

When using a reverse proxy, the browser-facing URL must be HTTPS; the internal proxy-to-application connection may remain HTTP. Ensure the proxy forwards the original scheme (`X-Forwarded-Proto: https`).

## Verify

```bash
docker compose ps
docker compose logs --tail=100 caltopo-history
curl http://127.0.0.1:8765/healthz
```

Expected:

```json
{"ok":true,"version":"0.10"}
```

## Persistent data

The default named volume is `caltopo_history_data`; the SQLite database is `/data/caltopo-history.db`. Normal container replacement does not delete the volume.

**Do not use `docker compose down -v` unless you intentionally want to delete all persistent application data.**

For a host bind mount instead:

```env
DATA_VOLUME=./data
```

## Updating

Create an online backup first:

```bash
./docker/backup-db.sh
```

Then rebuild/recreate. For the standard deployment:

```bash
docker compose build --pull
docker compose up -d
```

For standalone HTTPS:

```bash
docker compose -f compose.yaml -f compose.https.yaml build --pull
docker compose -f compose.yaml -f compose.https.yaml up -d
```

## Reverse-proxy examples

Apache:

```apache
ProxyPreserveHost On
ProxyPass / http://127.0.0.1:8765/
ProxyPassReverse / http://127.0.0.1:8765/
RequestHeader set X-Forwarded-Proto "https"
```

Nginx:

```nginx
location / {
    proxy_pass http://127.0.0.1:8765;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Why one Uvicorn worker?

CalTopo History contains its own scheduler. Multiple Uvicorn workers would start multiple schedulers and could poll/write concurrently, so the container deliberately starts one worker.

## Security defaults

- localhost-only application port by default
- non-root runtime process
- read-only root filesystem under Compose
- `/tmp` as tmpfs
- persistent writes limited to `/data`
- secure cookies enabled by default
- healthcheck included

## Container compliance

The repository workflow builds the image, generates an SPDX JSON SBOM with Syft and produces JSON plus human-readable Trivy license reports. Review those artifacts before publishing a binary image.
