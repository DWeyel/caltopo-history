# CalTopo History 1.0.1 — Docker deployment

This package contains the complete CalTopo History 1.0.1 application, a Docker image definition and Docker Compose deployment.

## Included

- application source (`app/`)
- `Dockerfile`
- `compose.yaml`
- optional standalone HTTPS overlay (`compose.https.yaml`, `Caddyfile`)
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
- CalTopo Team service-account credentials for CalTopo operations (they can be entered after first login)

## Fresh installation

```bash
unzip caltopo-history-v1.0.1-docker.zip
cd caltopo-history-v1.0.1-docker
cp .env.example .env
nano .env
```

For a normal fresh installation you **do not need to invent an application secret or initial admin password**. Leave these empty:

```dotenv
APP_PASSWORD=
APP_SECRET_KEY=
```

On first start the container automatically:

1. generates a 96-hex-character `APP_SECRET_KEY` and persists it as `/data/.app-secret-key`;
2. generates a strong temporary password for the `admin` account;
3. prints the temporary password to the first-start container log;
4. starts the application, hashes the password into SQLite and removes the plaintext handoff file.

CalTopo credentials are optional at this stage. You may place them in `.env`, or start the application first and enter them later under **Settings → Backup & CalTopo → CalTopo connection**.

Build and start from source:

```bash
docker compose up -d --build
```

Alternatively, after the 1.0.1 GitHub Release is published, use the prebuilt GHCR image that passed the release test/SBOM/license workflow:

```dotenv
IMAGE_REF=ghcr.io/dweyel/caltopo-history:1.0.1
```

Then:

```bash
docker compose pull
docker compose up -d
```

Read the initial administrator password:

```bash
docker compose logs caltopo-history
```

Look for the **CalTopo History initial administrator credentials** block. Sign in as `admin` and change the temporary password immediately under User Management. Operators with Docker-host access can read container logs, so treat the generated password as temporary.

Check status:

```bash
docker compose ps
curl http://127.0.0.1:8765/healthz
```

Expected response:

```json
{"ok":true,"version":"1.0.1"}
```

A fresh 1.0.1 database uses **English** as the UI language. CalTopo Credential ID/Secret, Team ID and service defaults can be configured from the Settings UI. See [`CALTOPO-SERVICE-ACCOUNT.md`](CALTOPO-SERVICE-ACCOUNT.md) for CalTopo-side setup and permissions.

By default the web service is published only on `127.0.0.1:8765`. Put Apache, Nginx, Caddy, Traefik or another TLS reverse proxy in front of it. If direct network access is intentional, change `BIND_IP` in `.env`.

## HTTPS and login cookies — important

The 1.0.1 default is:

```dotenv
COOKIE_SECURE=false
```

This allows a fresh installation to authenticate over either HTTP or HTTPS. For an Internet-facing HTTPS deployment, enable Secure session cookies under **Settings → Session security**, or set `COOKIE_SECURE=true` in `.env` before a Settings override exists.

A value saved in Settings overrides the `.env` fallback and takes effect immediately. Use the **use deployment environment** option in Settings to remove the override. If Secure cookies are enabled while the browser is using HTTP, the HTTP login session will no longer be usable; switch to the HTTPS URL.

HTTPS is still recommended for Internet-facing deployments. With `COOKIE_SECURE=false`, HTTP transports the session cookie without TLS protection.

### Option A: existing reverse proxy

Use Apache, Nginx, Traefik, Caddy or another TLS reverse proxy and keep `COOKIE_SECURE=true`. The browser-facing URL must be `https://...`; the internal proxy-to-application connection may remain HTTP. Ensure the proxy forwards the original scheme (`X-Forwarded-Proto: https`).

### Option B: standalone HTTPS with the included Caddy overlay

Set a public DNS name in `.env`:

```dotenv
DOMAIN=history.example.org
COOKIE_SECURE=true
```

The DNS A/AAAA record must point to the Docker host, and ports **80/tcp and 443/tcp** must be reachable from the Internet. Port **443/udp** enables HTTP/3 when available. Then start:

```bash
docker compose -f compose.yaml -f compose.https.yaml up -d --build
```

Caddy terminates TLS, automatically obtains/renews a public certificate for the configured domain and redirects HTTP to HTTPS. The CalTopo History container continues to speak plain HTTP only on the internal Docker network. See [STANDALONE-HTTPS.md](STANDALONE-HTTPS.md).

To stop the standalone stack:

```bash
docker compose -f compose.yaml -f compose.https.yaml down
```

Do not delete the Caddy volumes if you want to retain its certificate/account state.

## Persistent data

The default Compose configuration uses the named volume:

```text
caltopo_history_data
```

The database is:

```text
/data/caltopo-history.db
```

The database, snapshots, object history, users, settings, UI language and audit log survive image/container replacement.
The generated application secret also lives in the persistent volume as `/data/.app-secret-key`. **Do not delete or replace it on an existing installation.** Losing it invalidates active sessions and prevents decryption of a CalTopo Credential Secret saved through the Settings UI.

For disaster recovery, preserve **both** the SQLite database and `/data/.app-secret-key`. The helper `docker/export-data-volume.sh` exports the complete named volume and therefore includes both. `docker/backup-db.sh` creates a database-only backup for normal pre-update safety; a database-only copy is not sufficient to recover UI-managed encrypted CalTopo credentials if the original application secret is lost.

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

Schema/settings migrations run automatically at application startup. An existing v0.7 installation retains German as its initial 1.0.1 language so that the upgrade does not unexpectedly switch the UI; an admin can change it afterwards.

The persistent volume is not removed by `docker compose down` unless `-v` is explicitly supplied.

**Do not use `docker compose down -v` unless you intentionally want to delete the Docker volume and all application data.**

## Import an existing native installation

Copy the existing SQLite database to the Docker host, copy the relevant environment values into `.env`, build the image and run:

```bash
docker compose build
./docker/import-db.sh /path/to/caltopo-history.db
```

The application performs its normal migration when the container starts.

For the cleanest migration, stop the native service before copying the SQLite file. If it must remain running, use SQLite's online backup mechanism instead of copying only the `.db` file while WAL mode may be active.

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

CalTopo History v1.0.1 is licensed under `AGPL-3.0-only`. The web UI displays the configured source-code location. The default is the upstream GitHub repository. If you run a modified version, set `SOURCE_CODE_URL` to the Corresponding Source for that deployed version.

## Map tile provider

The default is the OpenStreetMap community raster tile service. Configure another provider when required:

```env
MAP_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
MAP_TILE_ATTRIBUTION='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
MAP_TILE_MAX_ZOOM=19
```

The OpenStreetMap community tile service is best-effort and intended for modest interactive use. It must not be used for bulk downloads, prefetching or offline tile generation. See `THIRD-PARTY-NOTICES.md`.


## Container compliance

The repository includes a GitHub Actions workflow that builds the application image, generates an SPDX JSON SBOM with Syft, and produces JSON plus human-readable Trivy license reports. Review these artifacts before publishing a binary container image.
