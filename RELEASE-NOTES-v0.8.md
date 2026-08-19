# CalTopo History v0.8 — Release Notes

## Overview

Version 0.8 adds full bilingual operation to CalTopo History while retaining the backup, history, restore, maintenance, audit, responsive UI, dark mode and Docker/native deployment capabilities from v0.7.

## New: English and German UI

The web interface now supports:

- English
- Deutsch

The language can be changed by an administrator under **Settings → Language**.

The selected language is stored in the application database and applies globally to the installation.

## Installation defaults and upgrade behavior

- Fresh v0.8 installations default to **English**.
- Existing v0.7 installations were German-only; when upgraded to v0.8 they initially remain **German** so the update does not unexpectedly change the active interface language.
- The language can be changed at any time by an administrator.

## Translated areas

The translation layer covers the complete application UI, including:

- login
- header/navigation/footer
- dashboard
- map management
- available-map picker
- map preview controls and messages
- current-object view
- snapshot list and comparison
- object history
- object restore
- point-in-time rollback
- settings
- user management
- restore audit
- maintenance
- disk-space warnings and backup lock status
- confirmation dialogs
- application-generated success, warning and error messages

Technical data originating directly from external systems or stored raw audit details is preserved as supplied rather than rewritten.

## Language-aware date display

Timestamps continue to use the configured `Europe/Berlin` timezone and correctly display CET/CEST.

Formatting now follows the selected UI language:

- English: `YYYY-MM-DD HH:MM:SS CET/CEST`
- German: `DD.MM.YYYY HH:MM:SS CET/CEST`

## Deployment

v0.8 remains available for:

- Docker / Docker Compose
- native Debian 12 + systemd
- ISPConfig reverse-proxy deployments

Existing v0.7 databases are migrated automatically when the application starts.

## Compatibility

All existing v0.7 data is retained, including:

- users and roles
- monitored maps
- snapshots
- object histories
- application settings
- restore audit entries
- maintenance data

No destructive schema migration is required for the language feature.
