# CalTopo History 1.0.1

Patch release focused on HTTP-first installation behavior and session-cookie configuration.

## Changes

- `COOKIE_SECURE` now defaults to `false` for fresh Docker and native Debian installations, so login works over plain HTTP without pre-configuration.
- Added an administrator setting for the Secure session-cookie flag under **Settings → Session security**.
- A Settings value overrides the deployment environment and can be reset back to the environment fallback.
- Changes to the Secure cookie policy take effect immediately for newly written session cookies; no container or service restart is required.
- Enabling Secure cookies while using an HTTP URL intentionally makes subsequent HTTP session requests unusable; switch to HTTPS.
- Updated Docker, Debian/ISPConfig and general documentation for the new default and override behavior.

## Upgrade behavior

Existing deployments keep any explicit `COOKIE_SECURE` value from their deployment environment. If no value or Settings override is present, the new 1.0.1 fallback is `false`. After upgrading, administrators can save an explicit value under **Settings → Session security** or reset the UI override to return control to the deployment environment.

## Security note

`COOKIE_SECURE=false` improves out-of-box compatibility but does not provide transport protection for the session cookie on plain HTTP. HTTPS with Secure session cookies remains recommended for Internet-facing deployments.
