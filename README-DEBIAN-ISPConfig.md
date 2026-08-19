# CalTopo History v0.9 on Debian 12 + ISPConfig 3

This deployment does not require Docker.

## Layout

- Application: `/opt/caltopo-history`
- Python virtual environment: `/opt/caltopo-history/.venv`
- SQLite database: `/var/lib/caltopo-history/caltopo-history.db`
- Upgrade database backups: `/var/lib/caltopo-history/caltopo-history.db.pre-*.bak`
- Secrets/config: `/etc/caltopo-history.env`
- Service: `caltopo-history.service`
- Internal listener: `127.0.0.1:8765` only
- Public HTTPS/TLS: ISPConfig website / reverse proxy

## Fresh installation

```bash
cd /root/caltopo-history-debian12-ispconfig-v0.9
chmod +x deploy/install-native-debian12.sh
./deploy/install-native-debian12.sh
```

Then configure `/etc/caltopo-history.env`. Required values include the CalTopo service-account credentials, initial admin password and a strong `APP_SECRET_KEY`.

Generate an application secret with:

```bash
openssl rand -base64 48
```

A fresh v0.9 installation starts with the UI in **English**. The administrator can select English or German under Settings.

## Upgrade

```bash
cd /root/caltopo-history-debian12-ispconfig-v0.9
chmod +x deploy/update-native-debian12.sh
./deploy/update-native-debian12.sh
```

The updater verifies available disk space, stops the service, creates a database safety copy, updates application code/dependencies, leaves `/etc/caltopo-history.env` unchanged, restarts the service and checks the health endpoint.

Existing users, maps, snapshots, object versions, settings and audit entries are retained.

## Verify

```bash
systemctl status caltopo-history --no-pager
curl http://127.0.0.1:8765/healthz
```

Expected:

```json
{"ok":true,"version":"0.9"}
```

Logs:

```bash
journalctl -u caltopo-history -f
```

## ISPConfig / Apache

In ISPConfig Apache Directives:

```apache
ProxyPreserveHost On
ProxyPass / http://127.0.0.1:8765/
ProxyPassReverse / http://127.0.0.1:8765/
RequestHeader set X-Forwarded-Proto "https"
```

Validate and reload:

```bash
apache2ctl configtest
systemctl reload apache2
```

Do not expose TCP/8765 directly to the Internet.

## v0.9 source and map-provider settings

The environment file supports:

```text
SOURCE_CODE_URL=https://github.com/DWeyel/caltopo-history
MAP_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
MAP_TILE_ATTRIBUTION=...
MAP_TILE_MAX_ZOOM=19
```

`SOURCE_CODE_URL` is shown in the web UI. If you deploy a modified AGPL version, set it to the Corresponding Source for the version actually running.

The OpenStreetMap community tile service is intended for normal interactive use and has usage-policy, availability and privacy implications. Configure another provider or self-hosted tiles where appropriate. See `THIRD-PARTY-NOTICES.md`.

## License

CalTopo History is licensed under `AGPL-3.0-only`. The native installer places the project licensing information and third-party notices alongside the application under `/opt/caltopo-history/`.

## Administration

Open **Settings** for language, global backup interval, CalTopo root Team ID, disk-space protection, users, restore audit and maintenance.

Maintenance shows logical backup payload sizes and physical database/application-data sizes. SQLite does not shrink its file immediately when rows are deleted; use the explicit `VACUUM` function after larger cleanup operations if filesystem space should be returned.

## CalTopo access model

- READ is sufficient for backing up a known Map ID in the current implementation.
- Restore operations require suitable write permission for affected object operations.
- Team catalog, map picker and title synchronization use the permissions actually granted to the configured service account; the application does not impose a fixed ADMIN requirement.

## Role model

- **Admin**: full system access.
- **User**: operational map/history/restore access without full administration.
- **View**: primarily read-oriented access with restore capability.

The literal username `admin` cannot be deleted, disabled or have its role changed. Only the signed-in `admin` can change that account's password.

## Back up CalTopo History itself

Include `/var/lib/caltopo-history/`. For a consistent external SQLite backup, use SQLite's backup mechanism or briefly stop the service before copying the database.

## Useful commands

```bash
systemctl status caltopo-history
systemctl restart caltopo-history
systemctl stop caltopo-history
journalctl -u caltopo-history --since today
```
