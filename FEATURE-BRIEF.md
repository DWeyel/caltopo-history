# Feature Brief — CalTopo History

## Overview

CalTopo History is a self-hosted backup, versioning, recovery, and audit solution for organizations that use CalTopo collaboratively.

Collaborative operational mapping creates an important recovery problem: an object that is accidentally deleted, overwritten, or modified may be difficult to reconstruct from the live map alone. CalTopo History adds an independent protection layer around the existing CalTopo workflow without requiring users to change how they work in CalTopo.

## The problem

Operational maps are often edited by multiple users at the same time. During an incident, exercise, or planning process, users may accidentally delete map objects, overwrite existing information, change geometry unintentionally, or need to understand how a map looked at an earlier point in time.

Traditional periodic exports provide some protection, but they create redundant copies, offer limited object-level history, are cumbersome to compare, and do not provide a dedicated restore audit trail.

CalTopo History addresses these limitations.

## Core concept

CalTopo History continuously monitors selected CalTopo maps through the CalTopo API.

Instead of simply creating full backups at fixed intervals, it analyzes the actual map state and records meaningful changes.

**Monitor → Detect Changes → Version → Compare → Restore → Audit**

Users continue working normally in CalTopo. CalTopo History operates independently in the background.

## Change-aware backup

CalTopo History periodically checks monitored maps for changes. A new snapshot is only created when the map state has actually changed.

Changes include:

- objects being added or deleted
- objects being restored
- changes to object geometry
- changes to titles or descriptions
- changes to symbols, colors, folder assignments, or other properties
- other modifications to the object data returned by CalTopo

This avoids creating large numbers of identical backups.

### Final-state snapshot

After a change has been detected, monitoring continues normally. If no additional changes occur for 30 minutes, CalTopo History creates one additional final-state snapshot. After that, no further identical snapshots are stored until another change is detected.

This creates a compact, event-oriented history rather than a large collection of repetitive scheduled exports.

## Map monitoring and discovery

Maps can be added to monitoring by selecting one or more available CalTopo maps, entering a Map ID manually, or using naming rules to automatically identify relevant maps.

The available-map interface can mirror the visible CalTopo team/account and folder hierarchy and display metadata such as map title, Map ID, owner, last modification time, sharing information, and monitoring status.

Each map can use either the global monitoring interval or its own interval override.

### Automatic monitoring expiration

Operational maps often only need active protection for a limited period. CalTopo History can automatically pause monitoring seven days after enrollment. The stored history remains available, and manual reactivation starts a new monitoring period.

## Map preview

Users can preview a CalTopo map before enabling monitoring.

The preview is loaded on demand to avoid unnecessary API requests. It displays the current geographic objects over an OpenStreetMap basemap and automatically fits the view to the available map objects.

For previously monitored maps, the application can fall back to the most recently stored local map state if live CalTopo data is temporarily unavailable.

## Object history

CalTopo History maintains object-level history in addition to full-map snapshots.

For each known object, users can review its title, type, ID, last detected modification, current existence state, and earlier versions.

Possible states include present, deleted, and restored.

A live title filter helps users locate objects quickly on large operational maps.

## Object-level restore

A deleted or incorrectly modified object can be restored from an earlier version.

Typical use cases include recovering an accidentally deleted marker, restoring a previous polygon geometry, recovering a modified line, or reverting an object to an earlier configuration.

Where possible, CalTopo History creates an additional pre-restore safety snapshot before modifying the live map.

## Point-in-time recovery

In addition to restoring individual objects, users can restore a map to a previous snapshot.

The application compares the selected historical state with the current state and determines which supported objects need to be restored or changed.

This provides a point-in-time recovery capability similar to versioned backup systems.

## Snapshot comparison

Any two snapshots of the same map can be compared.

The comparison identifies added, deleted, modified, and unchanged objects. Changes within existing objects are detected as well, including geometry and property changes.

This makes it possible to understand exactly how an operational map evolved between two points in time.

## Restore audit

Restore operations are security-relevant actions. CalTopo History therefore maintains a dedicated restore audit log.

Audit entries can include timestamp, username, user role, client IP address, map and object identifiers, object title, restore type, source snapshot or object version, and success or failure status.

Both successful and failed restore attempts can be recorded.

## Role-based access control

CalTopo History includes local user management with three roles:

- **Admin** — full access to system configuration, map management, users, maintenance, history, and restore functions.
- **User** — operational access to map monitoring, history, and restore functions without full system administration.
- **View** — primarily read-oriented access with restore capability, without administrative map or system management functions.

The primary `admin` account is protected against deletion, disabling, and role changes. Its password can only be changed by the `admin` user while logged in as that account.

## Maintenance and storage management

Historical data grows over time, so CalTopo History includes a dedicated maintenance area.

Administrators can manage old snapshots, historical object versions, archived map history, application database backups, and SQLite storage optimization.

The application reports storage consumption at several levels, including individual snapshots, per-map history, object history, SQLite database files, upgrade backups, and total application data consumption.

## Disk-space protection

A backup application should never become the reason a server runs out of disk space.

CalTopo History includes configurable warning and critical free-space thresholds. When the warning level is crossed, administrators receive a visible warning. When the critical level is crossed, new storage-producing backup operations are blocked automatically.

Backup activity resumes automatically once sufficient free space becomes available again.

Potentially storage-intensive maintenance operations are also checked against available disk capacity.

## Dashboard

The dashboard provides a centralized operational overview of monitored maps, monitoring state, recent backups, storage consumption, disk-space warnings, recent restore activity, and system status.

## Multi-language interface

CalTopo History supports English and German. English is the default language for new installations, and administrators can change the global UI language under Settings.

The localization covers navigation, dashboards, map management, object history, restore workflows, snapshot comparison, user management, audit views, maintenance, and application-generated messages.

## Dark mode and responsive design

The interface supports both light and dark themes and is designed for desktop systems, tablets, and smartphones.

Mobile optimizations include responsive navigation, touch-friendly controls, adaptive forms, responsive map previews, mobile-friendly metadata presentation, and controlled scrolling for large tables.

## Deployment options

CalTopo History can be deployed in two ways:

### Docker

The Docker deployment includes a Dockerfile, Docker Compose configuration, persistent data volume, health checks, environment-based configuration, database backup/import tools, non-root runtime, and a read-only container root filesystem.

### Native Linux

A native Debian deployment is also available using a Python virtual environment, systemd, Uvicorn, SQLite, and an Apache or Nginx reverse proxy.

## Persistent data and health monitoring

CalTopo History stores monitored maps, map metadata, snapshots, object versions, current object state, users, settings, and restore audit information in SQLite.

A dedicated health endpoint can be used by Docker, reverse proxies, and external monitoring platforms.

## Security model

Security-related capabilities include:

- role-based access control
- hashed local passwords
- protected administrator account
- restore auditing
- pre-restore safety snapshots
- disk-space protection
- environment-based CalTopo credentials
- reverse-proxy and HTTPS deployments
- non-root container execution
- read-only container filesystem

CalTopo credentials remain server-side and do not need to be exposed to normal application users.

## Operational value

CalTopo History is particularly useful wherever CalTopo maps are collaboratively maintained and operational information must remain recoverable, including emergency response, disaster response, wildfire operations, search and rescue, incident management, field operations, exercises, and operational planning.

It adds a recovery and accountability layer without replacing CalTopo itself.

## Summary

CalTopo History turns a live collaborative CalTopo map into a versioned and recoverable operational information source.

**If important map information is deleted, overwritten, or changed accidentally, the previous state does not have to be lost.**

CalTopo History provides the tools to identify what changed, understand when it changed, and restore the required information through an auditable recovery process.
