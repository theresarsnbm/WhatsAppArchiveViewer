from __future__ import annotations

from pathlib import Path
from tkinter import Tk, filedialog

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
        chat_dir = import_chat_export(export_dir, chat_name)
    except Exception as error:
        print(f"Fehler: {error}")
        return

    print()
    print("Import abgeschlossen.")
    print(f"Chat-Ordner: {chat_dir}")
    print_chat_summary(chat_dir)


def choose_export_folder() -> Path | None:
    """Öffnet einen macOS-Ordnerdialog und gibt den Pfad zurück."""

    root = Tk()
    root.withdraw()
    root.update()

    selected = filedialog.askdirectory(
        title="Entpackten WhatsApp-Export-Ordner auswählen",
        mustexist=True,
    )

    root.destroy()

    return Path(selected) if selected else None


def print_chat_summary(chat_dir: Path) -> None:
    """Zeigt an, welche Textdateien und wie viele Medien importiert wurden."""

    chat_files = sorted(chat_dir.glob("chat*.txt"))
    media_dir = chat_dir / "Media"

    media_count = 0
    if media_dir.is_dir():
        media_count = sum(1 for path in media_dir.rglob("*") if path.is_file())

    print()
    print("Übersicht:")
    for path in chat_files:
        print(f"  Text:   {path.name}")
    print(f"  Medien: {media_count} Datei(en) in {media_dir}")


if __name__ == "__main__":
    main()