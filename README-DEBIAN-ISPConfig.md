# CalTopo History v0.8 on Debian 12 + ISPConfig 3

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
cd /root/caltopo-history-debian12-ispconfig-v0.8
chmod +x deploy/install-native-debian12.sh
./deploy/install-native-debian12.sh
```

Then configure:

```bash
nano /etc/caltopo-history.env
```

Required values:

```text
CALTOPO_CREDENTIAL_ID=...
CALTOPO_CREDENTIAL_SECRET=...
APP_USERNAME=admin
APP_PASSWORD=...
APP_SECRET_KEY=...
COOKIE_SECURE=true
TZ=Europe/Berlin
```

Generate an application secret:

```bash
openssl rand -base64 48
```

`POLL_INTERVAL_SECONDS` is only the initial/bootstrap value. The global interval is configured in the web UI; per-map overrides are configured on the respective map page.

A fresh v0.8 installation starts with the UI in **English**. The administrator can select **English** or **Deutsch** under Settings.

## Upgrade from v0.7

```bash
cd /root/caltopo-history-debian12-ispconfig-v0.8
chmod +x deploy/update-native-debian12.sh
./deploy/update-native-debian12.sh
```

The updater:

1. verifies that the mandatory database copy plus the configured hard free-space reserve fits;
2. stops `caltopo-history.service`;
3. creates `/var/lib/caltopo-history/caltopo-history.db.pre-v0.8-YYYYMMDD-HHMMSS.bak`;
4. replaces application code and Python dependencies;
5. leaves `/etc/caltopo-history.env` unchanged;
6. starts the service and checks `http://127.0.0.1:8765/healthz`.

Existing users, maps, snapshots, object versions, settings and audit entries are retained. Because v0.7 was German-only, an upgraded installation starts v0.8 in German unless the administrator changes the new language setting. Fresh installations default to English.

## Verify after installation/update

```bash
systemctl status caltopo-history --no-pager
curl http://127.0.0.1:8765/healthz
```

Expected:

```json
{"ok":true,"version":"0.8"}
```

Logs:

```bash
journalctl -u caltopo-history -f
```

## ISPConfig / Apache

The reverse proxy remains unchanged. In ISPConfig Apache Directives:

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

Do not open TCP/8765 in the firewall.

## Administration

Open **Settings** for:

- Language (English / Deutsch)
- global backup interval and CalTopo root Team ID
- disk-space protection thresholds
- Users
- Restore audit
- Maintenance

Maintenance shows logical backup payload sizes and physical database/application-data sizes. SQLite does not shrink its file immediately when rows are deleted; use the explicit `VACUUM` function after larger cleanup operations if filesystem space should be returned.

## CalTopo access model

- READ is sufficient for backing up a known Map ID in the current implementation.
- Restore operations require suitable write permission for affected object operations.
- Team catalog / map picker / title synchronization use the permissions actually granted to the configured service account. The application does not impose a fixed ADMIN requirement.

## Role model

- **Admin**: full access including settings, intervals, rules, users, maintenance, monitoring management, backups and restores.
- **User**: can add/select maps, create manual snapshots, view history and perform restores.
- **View**: can view maps/history and perform restores, but cannot add maps or change configuration.

The literal username `admin` cannot be deleted, disabled or have its role changed. Only the signed-in `admin` can change that account's password.

## Back up CalTopo History itself

Include:

```text
/var/lib/caltopo-history/
```

For a consistent external SQLite backup, use SQLite's backup mechanism or briefly stop the service before copying the database.

## Useful commands

```bash
systemctl status caltopo-history
systemctl restart caltopo-history
systemctl stop caltopo-history
journalctl -u caltopo-history --since today
```
