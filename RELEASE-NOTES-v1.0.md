# CalTopo History 1.0

CalTopo History 1.0 is the first stable release.

## Configuration and first-start improvements

- CalTopo Credential ID and Credential Secret can now be managed by administrators from the Settings UI.
- A Credential Secret saved through the UI is encrypted at rest and is never rendered back to the browser.
- CalTopo API base URL, team discovery interval and periodic full-verification cadence are now configurable in Settings.
- Existing environment variables remain supported as deployment defaults/fallbacks.
- The Settings UI shows the status/source of the application secret without revealing it.
- Fresh Docker installations automatically generate and persist `APP_SECRET_KEY` when it is not explicitly supplied.
- Fresh native Debian installations automatically generate the application secret in a protected file.
- Fresh Docker and native installations automatically generate a strong temporary password for the initial `admin` account.
- The plaintext initial-password handoff file is deleted after the password has been hashed into the application database.
- Existing installations and upgrades retain their existing application secret and user passwords.

## CalTopo service-account documentation

- Added a dedicated service-account setup and permissions guide.
- WRITE is documented as the recommended permission level for the full current feature set based on practical CalTopo History testing.
- READ-only behavior is documented as a backup-only mode: readable maps can be backed up by explicit Map ID, while restore is unavailable and team catalog/discovery may be unavailable.
- The guide explicitly notes the current discrepancy between observed WRITE access to the team catalog and CalTopo's supported-API documentation, which currently states ADMIN for the account-data endpoint.
- The guide documents where the service account is created in CalTopo, when the one-time Credential Secret is shown, and how to obtain the Team ID.

## HTTPS and deployment

- The existing explicit warning remains: `COOKIE_SECURE=true` requires browser-facing HTTPS or login sessions cannot persist.
- Optional standalone Caddy HTTPS deployment remains available.
- Docker and native deployment documentation now describe automatic secret/password generation and the importance of preserving the application secret across updates.

## Security and compliance

- Added encrypted storage for UI-managed CalTopo Credential Secrets using the persistent installation application secret.
- AGPL-3.0-only licensing remains unchanged.
- Runtime dependency-license CI and container SBOM/license scanning remain release gates/review artifacts.

## Compatibility

- Existing databases, users, watched maps, snapshots, object history, audit records and settings are retained during upgrade.
- Existing environment-supplied CalTopo credentials continue to work until explicitly overridden in Settings.
