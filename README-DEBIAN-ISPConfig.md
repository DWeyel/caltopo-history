# CalTopo History 1.0 on Debian 12 + ISPConfig 3

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
cd /root/caltopo-history-debian12-ispconfig-v1.0
chmod +x deploy/install-native-debian12.sh
./deploy/install-native-debian12.sh
```

The installer now generates both security values required for first login:

- a persistent `APP_SECRET_KEY` in `/etc/caltopo-history.app-secret-key`;
- a strong temporary password for the initial `admin` account.

The temporary password is printed by the installer. It is also handed to the application through `/var/lib/caltopo-history/.initial-admin-password`; after the first successful database bootstrap the application hashes the password into SQLite and deletes that plaintext handoff file. Change the temporary password after the first login.

**Do not replace `/etc/caltopo-history.app-secret-key` on an existing installation.** It signs browser sessions and encrypts any CalTopo Credential Secret saved through the Settings UI.

For disaster recovery, back up `/etc/caltopo-history.app-secret-key` securely together with the SQLite database. A database backup without the original application secret retains map/history/user data but cannot decrypt a CalTopo Credential Secret that was saved through the Settings UI.

CalTopo credentials do not have to be present before the service starts. They can be entered in `/etc/caltopo-history.env` or, after login, under **Settings → Backup & CalTopo → CalTopo connection**. See [`CALTOPO-SERVICE-ACCOUNT.md`](CALTOPO-SERVICE-ACCOUNT.md) for the CalTopo-side setup and permission model.

Review deployment settings if required:

```bash
nano /etc/caltopo-history.env
```

Then start the service:

```bash
systemctl start caltopo-history
```

### Important: `COOKIE_SECURE` and HTTPS

The recommended/default production value is `COOKIE_SECURE=true`. This requires users to open the application through the HTTPS ISPConfig/Apache site. If somebody opens the backend directly as `http://host:8765` while secure cookies are enabled, valid credentials cannot create a persistent session because browsers do not send Secure cookies over HTTP. 1.0 displays a warning for this mismatch.

Keep port 8765 private and use the HTTPS reverse proxy. Set `COOKIE_SECURE=false` only for temporary trusted local HTTP testing.

`POLL_INTERVAL_SECONDS` is only the initial/bootstrap value. The global interval is configured in the web UI; per-map overrides are configured on the respective map page.

A fresh 1.0 installation starts with the UI in **English**. The administrator can select **English** or **Deutsch** under Settings.

## Upgrade from an earlier release

```bash
cd /root/caltopo-history-debian12-ispconfig-v1.0
chmod +x deploy/update-native-debian12.sh
./deploy/update-native-debian12.sh
```

The updater:

1. verifies that the mandatory database copy plus the configured hard free-space reserve fits;
2. stops `caltopo-history.service`;
3. creates `/var/lib/caltopo-history/caltopo-history.db.pre-v1.0-YYYYMMDD-HHMMSS.bak`;
4. replaces application code and Python dependencies;
5. leaves `/etc/caltopo-history.env` unchanged;
6. starts the service and checks `http://127.0.0.1:8765/healthz`.

Existing users, maps, snapshots, object versions, settings and audit entries are retained. Because v0.7 was German-only, an upgraded installation starts 1.0 in German unless the administrator changes the new language setting. Fresh installations default to English.

## Verify after installation/update

```bash
systemctl status caltopo-history --no-pager
curl http://127.0.0.1:8765/healthz
```

Expected:

```json
{"ok":true,"version":"1.0"}
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
- CalTopo Credential ID/Secret, API URL and root Team ID
- global backup interval, team discovery interval and full-verification cadence
- disk-space protection thresholds
- Users
- Restore audit
- Maintenance

Maintenance shows logical backup payload sizes and physical database/application-data sizes. SQLite does not shrink its file immediately when rows are deleted; use the explicit `VACUUM` function after larger cleanup operations if filesystem space should be returned.

## CalTopo access model

**WRITE is the recommended permission** for the complete feature set based on current practical testing. READ can support backup-only operation for explicitly enrolled readable Map IDs, but restore is not available and team catalog/discovery may be unavailable. CalTopo's current API page documents ADMIN for the team account-data endpoint even though current CalTopo History testing shows it working at WRITE. See [`CALTOPO-SERVICE-ACCOUNT.md`](CALTOPO-SERVICE-ACCOUNT.md) for the complete setup procedure and behavior matrix.

## Role model

- **Admin**: full access including settings, intervals, rules, users, maintenance, monitoring management, backups and restores.
- **User**: can add/select maps, create manual snapshots, view history and perform restores.
- **View**: can view maps/history and perform restores, but cannot add maps or change configuration.

The literal username `admin` cannot be deleted, disabled or have its role changed. Only the signed-in `admin` can change that account's password.

## Back up CalTopo History itself

Include both:

```text
/var/lib/caltopo-history/
/etc/caltopo-history.app-secret-key
```

Treat the application secret as sensitive backup material. For a consistent external SQLite backup, use SQLite's backup mechanism or briefly stop the service before copying the database.

## Useful commands

```bash
systemctl status caltopo-history
systemctl restart caltopo-history
systemctl stop caltopo-history
journalctl -u caltopo-history --since today
```


## License and public source

CalTopo History v1.0 is licensed under `AGPL-3.0-only`. For modified deployments, set `SOURCE_CODE_URL` in `/etc/caltopo-history.env` to the Corresponding Source for the version actually running.

The interactive basemap provider can be changed with `MAP_TILE_URL`, `MAP_TILE_ATTRIBUTION` and `MAP_TILE_MAX_ZOOM`. See `THIRD-PARTY-NOTICES.md` for OpenStreetMap policy and privacy notes.
