# CalTopo History v0.9 — Docker deployment

This package contains the complete CalTopo History v0.9 application, a Docker image definition and Docker Compose deployment.

## Included

- application source (`app/`)
- `Dockerfile`
- `compose.yaml`
- `.env.example`
- container healthcheck
- persistent SQLite data volume
- non-root application runtime (UID/GID 10001 after startup initialization)
- online SQLite backup helper (`docker/backup-db.sh`)
- native SQLite import helper (`docker/import-db.sh`)
- complete named-volume export helper (`docker/export-data-volume.sh`)
- Apache and Nginx reverse-proxy examples
- native Debian/ISPConfig deployment files under `deploy/`

## Requirements

- Docker Engine with Compose v2 (`docker compose`)
- Internet access during image build for Debian/Python dependencies
- CalTopo Team service-account credentials

## Fresh installation

```bash
unzip caltopo-history-v0.9-docker.zip
cd caltopo-history-docker-v0.9
cp .env.example .env
nano .env
```

Set at least:

```dotenv
CALTOPO_CREDENTIAL_ID=...
CALTOPO_CREDENTIAL_SECRET=...
APP_PASSWORD=...
APP_SECRET_KEY=...
```

Generate an application secret, for example:

```bash
openssl rand -hex 48
```

Build and start:

```bash
docker compose up -d --build
```

Check status:

```bash
docker compose ps
docker compose logs --tail=100 caltopo-history
curl http://127.0.0.1:8765/healthz
```

Expected response:

```json
{"ok":true,"version":"0.9"}
```

A fresh v0.9 database uses **English** as the UI language. Change it under **Settings → Language** if desired.

By default the web service is published only on `127.0.0.1:8765`. Put Apache, Nginx, Caddy, Traefik or another TLS reverse proxy in front of it. If direct network access is intentional, change `BIND_IP` in `.env`.

## HTTPS and login cookies

`COOKIE_SECURE=true` is recommended and requires HTTPS for browser login sessions. For a temporary local HTTP-only test:

```dotenv
COOKIE_SECURE=false
```

Do not use that setting for an Internet-facing deployment.

## Persistent data

The default Compose configuration uses the named volume `caltopo_history_data`. The database is `/data/caltopo-history.db`.

The database, snapshots, object history, users, settings, UI language and audit log survive image/container replacement.

For a host bind mount instead:

```dotenv
DATA_VOLUME=./data
```

The entrypoint initializes ownership of `/data` and then drops privileges. The application process runs as UID/GID `10001:10001`.

## Updating

Create a consistent online backup first:

```bash
./docker/backup-db.sh
```

Then rebuild/recreate:

```bash
docker compose build --pull
docker compose up -d
```

Schema/settings migrations run automatically at application startup. The persistent volume is not removed by `docker compose down` unless `-v` is explicitly supplied.

**Do not use `docker compose down -v` unless you intentionally want to delete the Docker volume and all application data.**

## Import an existing native installation

Copy the existing SQLite database to the Docker host, copy the relevant environment values into `.env`, build the image and run:

```bash
docker compose build
./docker/import-db.sh /path/to/caltopo-history.db
```

The application performs its normal migration when the container starts. For the cleanest migration, stop the native service before copying the SQLite file. If it must remain running, use SQLite's online backup mechanism instead of copying only the `.db` file while WAL mode may be active.

## Database backup

```bash
./docker/backup-db.sh
```

This creates a backup in the Docker volume (visible in Maintenance) and copies it to host-side `./backups/`.

## Full data-volume export

```bash
./docker/export-data-volume.sh
```

This writes a compressed disaster-recovery archive to `./backups/`.

## Reverse proxy

Apache example (`docker/apache-reverse-proxy.conf`):

```apache
ProxyPreserveHost On
ProxyPass / http://127.0.0.1:8765/
ProxyPassReverse / http://127.0.0.1:8765/
RequestHeader set X-Forwarded-Proto "https"
```

Nginx example (`docker/nginx-reverse-proxy.conf`):

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

CalTopo History contains its own scheduler in the FastAPI lifespan. Multiple Uvicorn workers would start multiple schedulers and could poll/write backups concurrently. The container deliberately starts exactly one worker.

## Security defaults

- web port binds to localhost by default
- runtime application process is non-root
- root filesystem is read-only under Compose
- `/tmp` is an in-memory tmpfs
- persistent writes are limited to `/data`
- `APP_SECRET_KEY` and initial `APP_PASSWORD` are required
- HTTPS secure cookies are enabled by default
- image includes a healthcheck

The container starts as root only long enough to ensure `/data` is writable by UID/GID 10001, then drops privileges before starting Uvicorn.

## Disk-space protection

The application evaluates the filesystem backing `/data`. Configurable warning and hard-stop thresholds are available in Settings. Below the hard threshold new backup/snapshot writes are blocked and resume automatically when free space recovers.

## License and source-code link

CalTopo History v0.9 is licensed under `AGPL-3.0-only`. The web UI displays the configured source-code location. The default is the upstream GitHub repository. If you run a modified version, set `SOURCE_CODE_URL` to the Corresponding Source for that deployed version.

## Map tile provider

The default is the OpenStreetMap community raster tile service. Configure another provider when required:

```env
MAP_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
MAP_TILE_ATTRIBUTION='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
MAP_TILE_MAX_ZOOM=19
```

The OpenStreetMap community tile service is best-effort and intended for modest interactive use. It must not be used for bulk downloads, prefetching or offline tile generation. See `THIRD-PARTY-NOTICES.md`.
