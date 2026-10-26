from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from app.importer import import_chat_export
from app.settings import get_archive_root, reset_archive_root, set_archive_root

EXPORT_PROMPT = "Entpackten WhatsApp-Export-Ordner auswählen"
ARCHIVE_PROMPT = "Neuen Archivordner auswählen"


def main() -> None:
    print("WhatsApp Chat Import")
    print("====================")
    print(f"Archiv: {get_archive_root()}")
    print()

    if input("Archivpfad ändern? (j/N): ").strip().lower() == "j":
        if not change_archive_root():
            return
        print(f"Neues Archiv: {get_archive_root()}")
        print()

    export_dir = choose_folder(EXPORT_PROMPT)
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
    print(f"Chat-Ordner:    {result.chat_dir}")
    print(f"Neue Textdatei: {result.imported_file.name}")
    print(f"Versionen:      {result.version_count}")

    if result.merge_result is None:
        print("Merge:          noch nicht nötig (nur eine Version)")
    else:
        print(f"Merge-Datei:    {result.merged_file.name}")
        print(f"Nachrichten:    {result.merge_result.unique_messages}")
        print(f"Duplikate:      {result.merge_result.duplicates_removed}")


def change_archive_root() -> bool:
    print()
    print("1. Neuen Ordner auswählen")
    print("2. Standardpfad wiederherstellen")
    print("3. Abbrechen")

    choice = input("Auswahl: ").strip()

    if choice == "1":
        print("Hinweis: Vorhandene Chats werden nicht verschoben,")
        print("nur der neue Ablageort wird gespeichert.")
        print()

        folder = choose_folder(ARCHIVE_PROMPT)
        if folder is None:
            print("Kein Ordner ausgewählt.")
            return False

        try:
            set_archive_root(folder)
        except (ValueError, OSError) as error:
            print(f"Fehler: {error}")
            return False

        return True

    if choice == "2":
        reset_archive_root()
        return True

    return False


def choose_folder(prompt: str) -> Path | None:
    """Nativer Ordnerdialog, plattformabhängig."""

    if sys.platform == "darwin":
        script = f'POSIX path of (choose folder with prompt "{prompt}")'
        return run_command(["osascript", "-e", script])

    if sys.platform.startswith("win"):
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$d = New-Object System.Windows.Forms.FolderBrowserDialog; "
            f"$d.Description = '{prompt}'; "
            "if ($d.ShowDialog() -eq 'OK') { $d.SelectedPath }"
        )
        return run_command(["powershell", "-NoProfile", "-Command", script])

    return ask_path_manually()


def run_command(command: list[str]) -> Path | None:
    """Führt den Dialog aus und liefert den gewählten Pfad."""

    try:
        completed = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError:
        return ask_path_manually()

    if completed.returncode != 0:
        return None

    value = completed.stdout.strip()
    return Path(value) if value else None


def ask_path_manually() -> Path | None:
    raw = input("Pfad: ").strip()
    if not raw:
        return None

    return Path(raw.strip("'\"")).expanduser()


if __name__ == "__main__":
    main()