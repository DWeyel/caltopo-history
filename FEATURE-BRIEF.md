# Feature Brief — CalTopo History

## Overview

**CalTopo History** is a self-hosted backup, versioning, recovery and audit layer for organizations that use CalTopo collaboratively.

It addresses a simple operational risk: when a shared map object is deleted, overwritten or changed accidentally, the previous state should not disappear with it.

Users continue to work normally in CalTopo while CalTopo History monitors selected maps through the CalTopo API and maintains an independent recovery history.

**Monitor → Detect Changes → Version → Compare → Restore → Audit**

## Change-aware backup

CalTopo History polls monitored maps on a configurable schedule but only stores a new snapshot when the actual map state changes. Changes include added or deleted objects as well as edits to existing geometry, titles, descriptions, symbols, colors, folders and other properties.

Thirty minutes after the last detected change, the application creates one final-state snapshot. It then remains quiet until another change occurs.

## Map discovery and monitoring

Maps can be enrolled by Map ID, selected from the visible CalTopo team catalog, selected in groups, or discovered through name rules. The picker can mirror the team/account and folder hierarchy and display owner, sharing state and update metadata where CalTopo provides it.

Each map can inherit the global polling interval or use its own override. Monitoring automatically pauses after seven days unless reactivated.

## Map preview

Available maps can be previewed on demand before enrollment. Current CalTopo objects are rendered over a configurable Leaflet basemap and the view automatically fits the relevant objects. For monitored maps, the application can fall back to the most recent local state if the live preview cannot be retrieved.

## Object history and restore

Every known object has its own version history and current state. Users can filter objects by title and see whether an object is present, deleted or restored.

Supported historical Marker and Shape versions can be restored individually. A complete snapshot can also be selected for point-in-time recovery of supported object types. Pre-restore safety snapshots reduce the risk of an accidental rollback.

## Snapshot comparison

Two snapshots can be compared to identify added, removed and changed objects, including changes inside existing geometry and properties.

## Restore audit

Restore activity is recorded with timestamp, user, role, client IP, map/object identifiers, object title, restore type, source version and success/failure status.

## Role-based access control

Three local roles are available:

- **Admin** — full system, map, user, maintenance and restore administration.
- **User** — operational map/history/restore access without full system administration.
- **View** — primarily read-oriented access with restore capability.

The primary `admin` account cannot be deleted, disabled or assigned another role; its password can only be changed by that account itself.

## Maintenance and storage protection

Administrators can prune old snapshots and object versions, purge archived map histories, remove upgrade database backups and run SQLite `VACUUM`.

Storage use is reported per snapshot, per map and for the overall application. Configurable warning and hard-stop thresholds prevent the backup service from filling the server disk. Backup writes resume automatically after free space recovers.

## User interface

The web interface includes:

- dashboard and monitoring status;
- English and German UI languages, with English as the fresh-install default;
- light and dark themes;
- responsive phone/tablet layouts;
- on-demand map previews;
- settings, user administration, restore audit and maintenance views.

## Deployment

CalTopo History supports:

- **Docker / Docker Compose** with persistent storage, health checks, non-root runtime and read-only root filesystem;
- **native Debian 12 / ISPConfig** deployment using a Python virtual environment, systemd, SQLite and a reverse proxy.

## Open-source model

Starting with v0.9, CalTopo History is licensed under **AGPL-3.0-only**. This keeps the software freely usable and modifiable while requiring operators of modified network-served versions to make the corresponding modified source available to their users.

The web interface contains a source-code link so operators can point users to the Corresponding Source for the deployed version. Third-party dependency and map-provider licensing is documented separately in `THIRD-PARTY-NOTICES.md`.

## Operational value

CalTopo History is intended for collaborative operational mapping where recoverability and accountability matter: emergency response, disaster response, wildfire operations, search and rescue, incident management, field operations, exercises and planning.

It does not replace CalTopo. It provides the recovery layer around it.
