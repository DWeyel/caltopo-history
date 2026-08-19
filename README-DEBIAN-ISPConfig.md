# CalTopo History v0.10 on Debian 12 + ISPConfig 3

This deployment runs natively with systemd/Uvicorn and uses ISPConfig/Apache or another local reverse proxy for public HTTPS.

## Layout

- Application: `/opt/caltopo-history`
- Python virtual environment: `/opt/caltopo-history/.venv`
- SQLite database: `/var/lib/caltopo-history/caltopo-history.db`
- Secrets/config: `/etc/caltopo-history.env`
- Internal listener: `127.0.0.1:8765`
- Public TLS: ISPConfig/reverse proxy

## Fresh installation

```bash
cd /root/caltopo-history-debian12-ispconfig-v0.10
chmod +x deploy/install-native-debian12.sh
./deploy/install-native-debian12.sh
nano /etc/caltopo-history.env
```

Required values include:

```env
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

## Important: `COOKIE_SECURE` and HTTPS

The recommended production setting is `COOKIE_SECURE=true`. This requires users to open the application through the HTTPS ISPConfig/Apache site.

Browsers do not send Secure cookies over plain HTTP. If somebody opens the backend directly as `http://host:8765` while `COOKIE_SECURE=true`, valid credentials cannot create a persistent login session and the browser returns to the login page. v0.10 displays an explicit warning for this mismatch.

Keep port 8765 private and use the HTTPS reverse proxy. Set `COOKIE_SECURE=false` only for temporary trusted local HTTP testing.

## Upgrade

```bash
cd /root/caltopo-history-debian12-ispconfig-v0.10
chmod +x deploy/update-native-debian12.sh
./deploy/update-native-debian12.sh
```

The updater creates a pre-update database backup named similar to:

```text
/var/lib/caltopo-history/caltopo-history.db.pre-v0.10-YYYYMMDD-HHMMSS.bak
```

Existing users, maps, snapshots, object versions, settings and audit entries are retained.

## Verify

```bash
systemctl status caltopo-history --no-pager
curl http://127.0.0.1:8765/healthz
```

Expected:

```json
{"ok":true,"version":"0.10"}
```

## ISPConfig / Apache

Use HTTPS on the public website and proxy internally to localhost:

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

## License/source

CalTopo History v0.10 is licensed under `AGPL-3.0-only`. For modified deployments, set `SOURCE_CODE_URL` in `/etc/caltopo-history.env` to the Corresponding Source for the version actually running.
