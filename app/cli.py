from __future__ import annotations

import subprocess
from pathlib import Path

from app.config import ARCHIVE_ROOT
from app.importer import import_chat_export


def main() -> None:
    print("WhatsApp Chat Import")
    print("====================")
    print(f"Archiv: {ARCHIVE_ROOT}")
    print()

    export_dir = choose_export_folder()
    if export_dir is None:
        print("Kein Ordner ausgewählt. Abbruch.")
        return

    print(f"Ausgewählt: {export_dir}")
    print()

    chat_name = input("Name des Chats: ").strip()
    if not chat_name:
        print("Kein Chatname eingegeben. Abbruch.")
        return

    try:
        result = import_chat_export(export_dir, chat_name)
    except Exception as error:
        print(f"Fehler: {error}")
        return

    print()
    print("Import abgeschlossen.")
    print(f"Chat-Ordner:      {result.chat_dir}")
    print(f"Neue Textdatei:   {result.imported_file.name}")
    print(f"Textversionen:    {result.version_count}")

    if result.merge_result is None:
        print("Merge:            noch nicht nötig (nur eine Version)")
    else:
        print(f"Merge-Datei:      {result.merged_file.name}")
        print(f"Nachrichten:      {result.merge_result.total_messages}")
        print(f"Eindeutig:        {result.merge_result.unique_messages}")
        print(f"Duplikate:        {result.merge_result.duplicates_removed}")

    print_chat_summary(result.chat_dir)


def choose_export_folder() -> Path | None:
    """Öffnet den nativen macOS-Ordnerdialog über AppleScript."""

    script = (
        'POSIX path of (choose folder with prompt '
        '"Entpackten WhatsApp-Export-Ordner auswählen")'
    )

    try:
        completed = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return ask_path_manually()

    if completed.returncode != 0:
        return None

    selected = completed.stdout.strip()
    return Path(selected) if selected else None


def ask_path_manually() -> Path | None:
    raw = input("Pfad zum Export-Ordner: ").strip()
    if not raw:
        return None

    return Path(raw.strip("'\"")).expanduser()


def print_chat_summary(chat_dir: Path) -> None:
    """Zeigt Textdateien und Anzahl der Mediendateien."""

    text_files = sorted(chat_dir.glob("chat*.txt")) + sorted(chat_dir.glob("merged_*.txt"))
    media_dir = chat_dir / "Media"

    media_count = 0
    if media_dir.is_dir():
        media_count = sum(1 for path in media_dir.rglob("*") if path.is_file())

    print()
    print("Übersicht:")
    for path in text_files:
        print(f"  Text:   {path.name}")
    print(f"  Medien: {media_count} Datei(en)")


if __name__ == "__main__":
    main()