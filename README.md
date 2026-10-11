# hotstocks-release

Kanal fuer **freigegebene, oeffentliche** Release-Pakete der Websites pharma-hotstocks.net und rohstoff-hotstocks.net.
Ein kleiner Agent auf dem Webserver holt (Pull) neue Eintraege unter `releases/<ID>/`, prueft Pfad, Dateityp, SHA-256 und erlaubte Skriptquellen,
sichert den Bestand, veroeffentlicht atomar, prueft den Origin und rollt bei Fehlern selbst zurueck.

- `releases/<ID>/manifest.json` und `releases/<ID>/files/<site>/<pfad>`
- Datei `PAUSE` im Wurzelverzeichnis stoppt alle Veroeffentlichungen.
- Keine privaten Daten, keine Entwuerfe, keine Zugangsdaten in diesem Repository.
