# CalTopo service account setup and permissions

CalTopo History authenticates to the supported CalTopo Teams API with a CalTopo **service account**. The service account is separate from the CalTopo History web users.

Official CalTopo reference: <https://training.caltopo.com/all_users/team-accounts/teamapi>

## Create the service account

1. Sign in to CalTopo as an administrator of the relevant Team.
2. Open the **Team Admin** page.
3. Open the **Details** tab.
4. Near the bottom of the page choose **Create a Service Account**.
5. Give the account a descriptive title and select its permission level.
6. Create the account and immediately copy the **Credential Secret**.

CalTopo shows the Credential Secret only once. Store it securely. The Credential ID can be viewed again later.

In CalTopo History 1.0, an administrator can enter the Credential ID and Credential Secret under **Settings → Backup & CalTopo → CalTopo connection**. The secret is never displayed again after saving and is encrypted before it is stored in the application database. Deployment environment variables remain supported as a fallback.

## Team ID

The root Team ID is also configured in CalTopo History under **Settings → Backup & CalTopo**.

CalTopo documents that the Team ID can be obtained from the Team Admin URL. The URL has the form:

```text
https://caltopo.com/group/{team_id}/admin/details
```

Use only the `{team_id}` value in CalTopo History.

## Recommended permission for CalTopo History: WRITE

For the current CalTopo History feature set, **WRITE is the recommended service-account permission**.

In practical testing, WRITE has been sufficient for:

- reading map data for backups and previews;
- reading the team catalog used by the map picker, folder hierarchy and automatic discovery;
- adding, editing and deleting supported map objects during snapshot rollback;
- restoring supported historical Marker/Shape objects.

CalTopo History does not create or delete entire CalTopo maps and does not change Team membership or map sharing settings, so MANAGE or ADMIN is not required for those functions.

### Important documentation discrepancy

CalTopo's current supported-API documentation states that `GET /api/v1/acct/{team_id}/since/{timestamp}` requires at least **ADMIN** permission. However, current CalTopo History testing has shown the team catalog endpoint working with a service account at **WRITE** permission.

CalTopo History therefore does **not** hard-code an ADMIN requirement. It calls the supported API and uses the permissions CalTopo actually grants. If CalTopo changes enforcement in the future and team discovery starts returning a permission error for WRITE, backups of explicitly configured maps may still work while catalog/discovery functions fail. In that situation, review the CalTopo permission level and the current CalTopo API documentation before increasing privileges.

## What happens with READ permission?

CalTopo's API documentation explicitly states that retrieving map data with:

```text
GET /api/v1/map/{map_id}/since/{timestamp}
```

requires at least **READ** access. Therefore a READ-only service account can still be useful for a backup-only installation.

With READ access, expect the following behavior:

| CalTopo History function | READ service account |
|---|---|
| Backup an explicitly added Map ID | Expected to work if the service account can read that map |
| Incremental/full map polling | Expected to work |
| Local snapshots and object history | Works |
| Snapshot comparison | Works |
| Local audit/history browsing | Works |
| Live map preview | Expected to work for readable maps |
| Team catalog / map picker | May fail; CalTopo currently documents the account endpoint as ADMIN-only |
| Regex-based team discovery | May fail for the same reason |
| Automatic team/folder/title synchronization | May fail for the same reason |
| Restore an object | Does not work with READ-only access |
| Roll back a whole map | Does not work with READ-only access |

If the team catalog is unavailable with READ, maps can still be enrolled manually by Map ID from the CalTopo History dashboard, provided the service account has read access to each map.

## Why WRITE instead of READ for the normal deployment?

CalTopo's general Team permission model describes **WRITE** as the level that can add, edit and delete objects on Team maps. CalTopo History's rollback feature may need all three operations in order to reproduce a historical map state. READ is therefore intentionally treated as a backup-only mode rather than the recommended full-feature configuration.

## Credential rotation

To rotate the CalTopo service-account credential:

1. Create/rotate the service-account credential in CalTopo according to the current Team Admin workflow.
2. Copy the new secret when CalTopo shows it.
3. In CalTopo History open **Settings → Backup & CalTopo → CalTopo connection**.
4. Update the Credential ID if it changed.
5. Enter the new Credential Secret in **Replace credential secret** and save.
6. Confirm that the team catalog refresh succeeds and run a manual backup of a test map.

The old secret is not shown by CalTopo History and is not written to the audit log.

## Application secret vs. CalTopo credential secret

These are different secrets:

- **CalTopo Credential Secret** authenticates CalTopo History to the CalTopo API.
- **APP_SECRET_KEY** is an internal CalTopo History installation secret used for web-session signing and for encrypting a Credential Secret saved through the Settings UI.

CalTopo History 1.0 generates `APP_SECRET_KEY` automatically on a fresh installation. Do not replace it on an existing installation unless intentionally rotating it. Changing it invalidates active web sessions and makes a Credential Secret previously encrypted through the Settings UI unreadable until that CalTopo secret is entered again.
