# Standalone HTTPS with Caddy

CalTopo History can use an existing reverse proxy or the optional Caddy Compose overlay included with v0.10.

## Why Caddy is separate

The application container intentionally serves plain HTTP internally. TLS termination, ACME certificate management and HTTP-to-HTTPS redirection are handled by the dedicated Caddy container. This keeps certificate/private-key lifecycle out of the application container.

Caddy supports automatic HTTPS for public DNS names and automatically renews managed certificates. Official documentation: `https://caddyserver.com/docs/automatic-https`.

## Requirements

- a public DNS name, for example `history.example.org`
- A/AAAA DNS records pointing to the Docker host
- inbound port 80/tcp available for ACME/HTTP redirect
- inbound port 443/tcp available for HTTPS
- optional 443/udp for HTTP/3
- `COOKIE_SECURE=true`

## Configuration

In `.env`:

```env
DOMAIN=history.example.org
COOKIE_SECURE=true
```

Start:

```bash
docker compose -f compose.yaml -f compose.https.yaml up -d --build
```

Stop without deleting persistent Caddy state:

```bash
docker compose -f compose.yaml -f compose.https.yaml down
```

Do not append `-v` unless you intentionally want to delete the application and Caddy volumes.

## Existing reverse proxy

Do not use the Caddy overlay if Apache, Nginx, Traefik, ISPConfig or another service already owns ports 80/443. Use the standard `compose.yaml` and configure that existing proxy to forward to `127.0.0.1:8765` with `X-Forwarded-Proto: https`.

## Cookie behavior

`COOKIE_SECURE=true` is required for a normal secure production deployment. A Secure cookie cannot be used over plain HTTP. If the browser URL is `http://...`, correct login credentials cannot produce a persistent session. v0.10 warns about this directly on the login page.

## Caddy license

The optional overlay references the official `caddy:2-alpine` image. Caddy is licensed under Apache-2.0 and runs as a separate service; it is not incorporated into the CalTopo History application image.
