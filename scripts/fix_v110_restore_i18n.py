from pathlib import Path

p = Path('app/i18n.py')
s = p.read_text()
replacements = {
'        "archive_history_help": "Diese Map ist lokal archiviert und wird nicht überwacht. Gespeicherte Historie kann ohne Neustart der Überwachung angesehen, verglichen, heruntergeladen und wiederhergestellt werden. Die ursprüngliche CalTopo-Map muss zum Wiederherstellen existieren, entsperrt und beschreibbar sein. Zum erneuten Überwachen die Map-ID im Dashboard hinzufügen.",':
'        "archive_history_help": "Diese Map ist lokal archiviert und wird nicht überwacht. Gespeicherte Historie kann ohne Neustart der Überwachung angesehen, verglichen, heruntergeladen und wiederhergestellt werden. Wurde die ursprüngliche Map gelöscht, kann ein Snapshot mit gespeicherten Team-Metadaten als neue CalTopo-Map mit neuer Map-ID wiederhergestellt werden.",',
'        "restore_map_to_time": "Objekte in der bestehenden Map zurücksetzen",':
'        "restore_map_to_time": "Map zurücksetzen oder neu erstellen",',
'        "restore_map_explanation": "Die App erstellt zuerst einen frischen Pre-Restore-Snapshot. Danach werden dokumentiert unterstützte Marker/Shapes geändert, neu angelegt oder entfernt. Andere Objekttypen werden übersprungen und im Audit protokolliert.",':
'        "restore_map_explanation": "Existiert die Map noch, erstellt die App zuerst einen frischen Pre-Restore-Snapshot und ändert, erstellt oder entfernt danach unterstützte Marker/Shapes. Wurde die Map gelöscht und wurden ihre Team-Metadaten gespeichert, erstellt CalTopo History aus dem Snapshot eine neue Map. CalTopo vergibt dabei eine neue Map-ID.",',
'        "restore_requirements": "Die ursprüngliche CalTopo-Map muss noch existieren, entsperrt sein und Schreibzugriff für das Servicekonto erlauben. Ein Rollback erstellt keine gelöschte Map neu und stellt keine Map-Einstellungen oder Freigaben wieder her. Bei einer gelöschten Map den Snapshot als GeoJSON herunterladen und unterstützte Objekte in eine neue CalTopo-Map importieren. Eine gesperrte Map vor einem erneuten Versuch durch einen Team-Manager oder Admin entsperren lassen. Schreibvorgänge sind nicht atomar: Einige Änderungen können vor einem Fehler erfolgreich sein. Vor einem erneuten Versuch das Restore-Audit prüfen.",':
'        "restore_requirements": "Bestehende Maps müssen entsperrt und für das Servicekonto beschreibbar sein. Gelöschte Maps können nur automatisch neu erstellt werden, wenn der Snapshot die ursprünglichen Team-Metadaten enthält; die neue Map erhält eine neue CalTopo-Map-ID. Bei der Neuerstellung werden unterstützte Marker/Shapes sowie gespeicherter Titel, Modus, Freigabe und Layer-Konfiguration übernommen. Die neue Map sollte vor dem operativen Einsatz geprüft werden. Schreibvorgänge in bestehende Maps sind nicht atomar: Einige Änderungen können vor einem Fehler erfolgreich sein.",',
'        "rollback_incomplete": "Rollback mit Fehlern beendet; einige Änderungen wurden möglicherweise angewendet. Vor einem erneuten Versuch das Restore-Audit prüfen und sicherstellen, dass die Map entsperrt und beschreibbar ist: {stats}",':
'        "rollback_incomplete": "Rollback mit Fehlern beendet; einige Änderungen wurden möglicherweise angewendet. Das Restore-Audit prüfen. Eine gesperrte Map oder fehlende UPDATE-Berechtigung kann diese Fehler verursachen: {stats}",',
}
for old, new in replacements.items():
    if old not in s:
        raise SystemExit(f'missing German translation match: {old[:100]}')
    s = s.replace(old, new, 1)
p.write_text(s)
