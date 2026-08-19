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

The translation layer covers the complete application UI, including login, navigation, map management, previews, object history, restores, settings, user management, audit, maintenance, disk-space warnings, confirmation dialogs and application-generated messages.

## Language-aware date display

Timestamps continue to use `Europe/Berlin` and correctly display CET/CEST.

- English: `YYYY-MM-DD HH:MM:SS CET/CEST`
- German: `DD.MM.YYYY HH:MM:SS CET/CEST`

## Deployment

v0.8 remains available for Docker / Docker Compose and native Debian 12 + systemd / ISPConfig reverse-proxy deployments.

## Compatibility

All existing v0.7 data is retained, including users and roles, monitored maps, snapshots, object histories, settings, restore audit entries and maintenance data.
