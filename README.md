# WhatsApp Archive Viewer

Lokales Archiv für WhatsApp-Chat-Exporte: Exporte einlesen, mehrere Versionen
eines Chats zu einer durchsuchbaren Textdatei zusammenführen und die Chats
anschließend in einer Desktop-Oberfläche lesen.

Alles läuft offline auf dem eigenen Rechner. Es gibt keinen Server, keinen
Upload und keine Cloud-Anbindung.

Lizenz: MIT (siehe [LICENSE](LICENSE)).

## Status

| Bereich | Stand |
|---|---|
| Einstellungen (Archivpfad, Speicherort) | fertig |
| Import von Export-Ordnern inkl. Medien | fertig |
| Parser für das WhatsApp-Textformat | fertig |
| Zusammenführen mehrerer Export-Versionen | fertig |
| CLI zum Importieren | fertig |
| Grafische Oberfläche (Chatliste, Verlauf) | geplant |
| Suche im aktuellen Chat | geplant |
| Kalender zum Springen auf Tage | geplant |
| Bilderübersicht pro Chat | geplant |

Bis die Oberfläche fertig ist, ist das Projekt ein Kommandozeilen-Werkzeug, das
eine saubere Archivstruktur erzeugt.

## Voraussetzungen

- Python 3.11 oder neuer (wegen `Path.is_relative_to` und `removeprefix`)
- Ein entpackter WhatsApp-Export (der Ordner mit `chat.txt` und `Media/`)
- Keine externen Abhängigkeiten für Import und Merge

## Installation

```bash
git clone <repository-url>
cd whatsapp-archive-viewer
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
```

Der Import läuft direkt aus dem Projektordner, eine Installation als Paket ist
nicht nötig.

## Import benutzen

```bash
python -m app.cli
```

Der Ablauf ist bewusst dialoggeführt:

1. Der aktuelle Archivordner wird angezeigt; er kann geändert oder auf den
   Standard zurückgesetzt werden.
2. Ein nativer Ordnerdialog öffnet sich zur Auswahl des entpackten Exports.
3. Der Chatname wird abgefragt.
4. Der Import kopiert `chat.txt` und alle Mediendateien ins Archiv.
5. Ab der zweiten Version eines Chats wird automatisch zusammengeführt.

Beim Zusammenführen gilt:

- Nachrichten werden nach Zeitstempel sortiert.
- Identische Nachrichten aus mehreren Exporten erscheinen nur einmal. Gleich
  heißt: gleicher Zeitstempel, gleicher Absender, gleicher Text und gleiche
  Anhangsdateinamen.
- Die Originaldateien bleiben unverändert erhalten; es entsteht zusätzlich eine
  Datei `merged_JJJJ-MM-TT_HH-MM-SS.txt`.

Kopiert werden nur echte Mediendateien; `chat.txt`, ZIP-Dateien und
`__MACOSX`-Reste werden übersprungen.

## Archivstruktur

```
WhatsAppArchive/
└── chats/
    └── Chatname/
        ├── chat_name.txt          # ursprünglicher Chatname
        ├── chat.txt               # erste importierte Version
        ├── chat_version_2.txt     # weitere Exporte
        ├── merged_2026-01-14_10-00-00.txt
        └── Media/
            └── 00000002-PHOTO-2025-06-01-12-00-00.jpg
```

Der Chatordner wird aus dem Chatnamen erzeugt und dabei plattformneutral
bereinigt: unzulässige Zeichen werden ersetzt, Windows-Gerätenamen wie `CON`
entschärft und die Länge auf 80 Zeichen begrenzt. Groß- und Kleinschreibung
wird beim Wiederfinden ignoriert, damit macOS und Windows sich gleich verhalten.

## Einstellungen

Einstellungen liegen nicht im Projektordner, sondern im Konfigurationsordner des
Benutzers:

- macOS: `~/Library/Application Support/WhatsAppArchiveViewer/settings.json`
- Windows: `%APPDATA%\WhatsAppArchiveViewer\settings.json`
- Linux: `~/.config/WhatsAppArchiveViewer/settings.json`

Gespeichert wird dort nur der Archivpfad:

```json
{
  "archive_root": "/Users/benutzer/WhatsAppArchive"
}
```

Der aktuelle Archivpfad ergibt sich in dieser Reihenfolge:

1. Umgebungsvariable `WA_ARCHIVE_ROOT`
2. gespeicherte Einstellung
3. Standardordner `~/WhatsAppArchive`

Ohne Einstellungsdatei startet das Programm also mit sinnvollen Vorgaben. Die
Datei wird atomar geschrieben, damit ein Abbruch keine halbe Datei hinterlässt.

## Geplante Oberfläche

Die Oberfläche wird mit Qt (PySide6) umgesetzt und besteht aus einer Chatliste
links und dem Chatverlauf rechts. Suche, Kalender und Medienübersicht sitzen in
der Kopfzeile des jeweils geöffneten Chats, nicht in einer globalen Seitenleiste.

- **Suche:** durchsucht ausschließlich den aktuellen Chat, zeigt Trefferzähler
  und springt per Tastatur von Treffer zu Treffer. Der Verlauf bleibt dabei
  vollständig sichtbar.
- **Kalender:** ausklappbar, markiert alle Tage mit Nachrichten und springt beim
  Klick auf die erste Nachricht dieses Tages.
- **Bilderübersicht:** Raster der Bilder eines Chats, gruppiert nach Monaten,
  mit Sprung zur zugehörigen Nachricht.

Eigene Absendernamen werden in den Einstellungen gepflegt, nicht im Quellcode.

## Projektstruktur

```
app/
├── config.py      # Konstanten: Ordnernamen, Standardpfade
├── settings.py    # Laden und Speichern der Benutzereinstellungen
├── parser.py      # WhatsApp-Textformat, Anhänge, Medientypen
├── archive.py     # Chats auflisten und einlesen
├── importer.py    # Exporte ins Archiv kopieren
├── merger.py      # Versionen zusammenführen und Duplikate entfernen
└── cli.py         # Kommandozeilen-Ablauf
```

## Bekannte Grenzen

- Das Textformat wird zeilenweise erkannt; Systemmeldungen und Umfragen werden
  als normale Nachrichten behandelt.
- Verschlüsselte oder beschädigte Mediendateien werden nicht repariert, sondern
  beim Lesen als fehlend gemeldet.
- Zeitstempel werden ohne Zeitzoneninformation gelesen.
- Es gibt noch keine automatisierten Tests.

## Was nicht ins Repository gehört

Persönliche Daten bleiben lokal. Ausgeschlossen sind:

```gitignore
# Persönliche Einstellungen
settings.json

# Archivdaten und Exporte
WhatsAppArchive/
*.zip

# Python
__pycache__/
*.pyc
.venv/
```

Wichtig: Eine Zeile in `.gitignore` wirkt nur auf noch nicht erfasste Dateien.
Bereits versionierte Dateien müssen zusätzlich mit `git rm --cached <datei>`
aus dem Index genommen werden; Inhalte aus früheren Commits verschwinden dadurch
nicht. Beispiele in Code, Tests und Dokumentation verwenden neutrale Namen wie
`Vorname Nachname`.

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Der vollständige Lizenztext liegt in
der Datei [LICENSE](LICENSE).

Kurz zusammengefasst: Nutzung, Veränderung und Weitergabe sind erlaubt, auch
kommerziell und auch in veränderter Form. Bedingung ist, dass der
Copyright-Hinweis und der Lizenztext in Kopien oder wesentlichen Teilen erhalten
bleiben. Es gibt keine Gewährleistung und keine Haftung.

Beim Weiterverwenden empfiehlt es sich, den Copyright-Hinweis in der `LICENSE`
auf das eigene Jahr und den eigenen Namen anzupassen.
