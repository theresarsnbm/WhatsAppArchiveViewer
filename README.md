# WhatsApp Archive Viewer

Lokale Anwendung zum Anzeigen exportierter WhatsApp-Chats. Die App liest die
Exportordner ein, legt sie in einem eigenen Archiv ab und führt mehrere
Versionen desselben Chats zu einer chronologischen Ansicht zusammen.

Alles bleibt lokal: keine Cloud, keine Datenbank, keine Netzwerkverbindung.

## Funktionen

- Import eines entpackten WhatsApp-Exports (`chat.txt` + Medien auf einer Ebene)
- Automatische Erkennung, ob es sich um eine neue Version eines bestehenden Chats handelt
- Medien werden anhand ihres Dateinamens abgeglichen; nur neue Dateien werden kopiert
- Textversionen bleiben vollständig erhalten (`chat.txt`, `chat_version_2.txt`, ...)
- Automatischer Merge ab zwei Versionen in eine `merged_...txt`
- Deduplizierung über Zeitstempel, Absender, Text und Anhangsnamen
- Konfigurierbarer Archivpfad, gespeichert im Benutzerprofil
- Konsolen-Interface (GUI in Arbeit)

## Voraussetzungen

- Python 3.11 oder neuer (entwickelt mit Python 3.14)
- macOS oder Windows
- Für die spätere GUI: PySide6

## Installation

```bash
git clone https://github.com/<DEIN-NAME>/WhatsAppArchiveViewer.git
cd WhatsAppArchiveViewer

python3 -m venv .venv
source .venv/bin/activate        # macOS
# .venv\Scripts\activate         # Windows

python -m pip install -U pip
python -m pip install -r requirements.txt
```

`requirements.txt` ist aktuell leer, weil Import, Parser und Merge ausschließlich
die Python-Standardbibliothek nutzen.

## Nutzung

```bash
python -m app.cli
```

Ablauf:

1. Das Programm zeigt den aktuellen Archivpfad an.
2. Optional lässt sich ein neuer Archivordner wählen.
3. Danach öffnet sich der native Ordnerdialog für den entpackten Export.
4. Chatnamen eingeben.
5. Der Import läuft, bei mehreren Versionen wird automatisch gemergt.

Beispielausgabe:

```text
Import abgeschlossen.
Chat-Ordner:    /Users/theresa/WhatsAppArchive/chats/Theresa
Neue Textdatei: chat_version_2.txt
Versionen:      2
Merge-Datei:    merged_2026-10-26_19-40-00.txt
Nachrichten:    118
Duplikate:      22
```

## Archivstruktur

```text
WhatsAppArchive/
└─ chats/
   └─ Theresa/
      ├─ chat_name.txt
      ├─ chat.txt
      ├─ chat_version_2.txt
      ├─ merged_2026-10-26_19-40-00.txt
      └─ Media/
         ├─ 00000002-PHOTO-2024-12-05-10-18-05.jpg
         ├─ 00000025-Spicker2.pdf
         ├─ 00000053-AUDIO-2026-08-28-22-52-36.opus
         └─ 00000056-VIDEO-2026-10-25-17-37-50.mp4
```

- `chat.txt` ist die erste importierte Version.
- `chat_version_N.txt` sind weitere Importe desselben Chats.
- `merged_*.txt` ist die zusammengeführte Anzeigedatei mit Zeitstempel im Namen.
- `Media/` ist der einzige Medienordner des Chats. Neue Dateien werden ergänzt,
  vorhandene Dateinamen nicht überschrieben.

Die Originaldateien werden nie verändert.

## Unterstütztes Exportformat

Die App erwartet das Textformat, das WhatsApp beim Export erzeugt:

```text
[05.12.24, 10:18:05] Du: Nachricht
[05.12.24, 10:18:05] Theresa Rosenbaum: <Anhang: 00000002-PHOTO-2024-12-05-10-18-05.jpg>
```

Mehrzeilige Nachrichten werden korrekt zusammengeführt, unsichtbare
Steuerzeichen (U+200E, U+200F, BOM) werden entfernt. Anhänge werden über den
Dateinamen in `Media/` aufgelöst; fehlende Dateien führen nicht zum Absturz,
sondern werden als nicht vorhanden markiert.

## Merge-Verhalten

Ein Merge läuft automatisch, sobald mindestens zwei Textversionen vorliegen.
Zwei Nachrichten gelten als identisch, wenn alle vier Merkmale übereinstimmen:

1. Zeitstempel
2. Absender (ohne Groß-/Kleinschreibung)
3. Text mit normalisierten Leerzeichen
4. sortierte Liste der Anhangsdateinamen

Der Merge schreibt immer eine neue Datei und überschreibt keine bestehende.
Mehrfaches Mergen erzeugt entsprechend mehrere `merged_*.txt` mit
unterschiedlichen Zeitstempeln.

## Archivpfad ändern

Der Pfad wird nicht im Code hinterlegt, sondern in einer Einstellungsdatei:

- macOS: `~/Library/Application Support/WhatsAppArchiveViewer/settings.json`
- Windows: `%APPDATA%\WhatsAppArchiveViewer\settings.json`

```json
{
  "archive_root": "/Volumes/WhatsApp/WhatsAppArchive"
}
```

Priorität beim Laden:

1. Umgebungsvariable `WA_ARCHIVE_ROOT`
2. gespeicherte Einstellung
3. Standardordner `~/WhatsAppArchive`

Beim Ändern des Pfads werden vorhandene Chats **nicht** verschoben, es wird nur
der neue Ablageort gespeichert.

## Projektstruktur

```text
WhatsAppArchiveViewer/
├─ app/
│  ├─ config.py      Konstanten (Ordnernamen, Limits)
│  ├─ settings.py    Archivpfad und Persistenz
│  ├─ archive.py     Chats aus dem Archiv einlesen
│  ├─ parser.py      chat.txt -> Message-Objekte
│  ├─ merger.py      Versionen zusammenführen und deduplizieren
│  ├─ importer.py    Import inklusive Auto-Merge
│  ├─ cli.py         Konsolen-Einstieg
│  └─ ui/            GUI (folgt)
├─ tests/
├─ .gitignore
├─ LICENSE
├─ THIRD_PARTY_NOTICES.md
└─ requirements.txt
```

Die Logik ist bewusst frei von GUI-Abhängigkeiten: Parser, Merge und Import
lassen sich ohne Display testen.

## Tests

```bash
python -c "import app.cli, app.importer, app.merger, app.archive, app.parser, app.settings; print('Imports ok')"
```

```bash
python - <<'PY'
from app.archive import list_chats
from app.parser import parse_chat_file

for entry in list_chats():
    messages = parse_chat_file(entry.display_file)
    missing = sum(
        1
        for message in messages
        for attachment in message.attachments
        if not attachment.exists
    )
    print(f"{entry.name}: {len(messages)} Nachrichten, {missing} fehlende Medien")
PY
```

## Roadmap

- [x] Import einzelner Exporte
- [x] Versionierung und automatischer Merge
- [x] Plattformneutraler Archivpfad
- [ ] GUI mit Chatliste und Nachrichtenansicht
- [ ] Medienvorschau für Bilder, Videos, Audio und PDF
- [ ] Volltextsuche
- [ ] macOS-Bundle via PyInstaller

## Datenschutz

Chats und Medien verlassen den Rechner nicht. Es gibt keine Synchronisation und
keine Telemetrie. Das Archivverzeichnis ist in `.gitignore` eingetragen und
sollte nie in ein Repository gelangen.

## Lizenz

Der eigene Code steht unter der MIT-Lizenz, siehe [LICENSE](LICENSE).
Verwendete Fremdbibliotheken und ihre Lizenzen sind in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) dokumentiert.

Diese Anwendung verwendet Qt for Python (PySide6) unter LGPLv3. GPL-only-Module
wie Qt Charts, Qt Data Visualization oder Qt Virtual Keyboard werden nicht
verwendet.
