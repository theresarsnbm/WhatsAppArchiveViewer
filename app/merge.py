from __future__ import annotations

import sys
from pathlib import Path

from app.config import ARCHIVE_ROOT, CHATS_DIR_NAME
from app.merger import MergeError, merge_chat_versions


def main() -> None:
    chats_root = Path(ARCHIVE_ROOT).expanduser() / CHATS_DIR_NAME

    if not chats_root.is_dir():
        print(f"Kein Chat-Archiv gefunden: {chats_root}")
        return

    chats = sorted(path for path in chats_root.iterdir() if path.is_dir())

    if not chats:
        print("Es sind noch keine Chats importiert.")
        return

    chat_dir = resolve_chat_dir(chats, sys.argv[1:])
    if chat_dir is None:
        return

    try:
        result = merge_chat_versions(chat_dir)
    except MergeError as error:
        print(f"Fehler: {error}")
        return

    print()
    print("Merge abgeschlossen.")
    print(f"Chat:            {chat_dir.name}")
    print(f"Versionen:       {len(result.version_files)}")
    print(f"Nachrichten:     {result.total_messages}")
    print(f"Eindeutig:       {result.unique_messages}")
    print(f"Duplikate:       {result.duplicates_removed}")
    print(f"Neue Datei:      {result.merged_file.name}")


def resolve_chat_dir(chats: list[Path], arguments: list[str]) -> Path | None:
    """Nutzt ein Argument als Chatnamen oder fragt interaktiv nach."""

    if arguments:
        query = " ".join(arguments).strip().casefold()

        for chat_dir in chats:
            if chat_dir.name.casefold() == query:
                return chat_dir

        print(f"Kein Chat gefunden für: {' '.join(arguments)}")
        print_chats(chats)
        return None

    print("Verfügbare Chats:")
    print_chats(chats)

    selection = input("Chatname: ").strip()
    if not selection:
        print("Keine Auswahl. Abbruch.")
        return None

    return resolve_chat_dir(chats, [selection])


def print_chats(chats: list[Path]) -> None:
    for index, chat_dir in enumerate(chats, start=1):
        versions = len(list(chat_dir.glob("chat*.txt")))
        print(f"  {index}. {chat_dir.name} ({versions} Textversion(en))")


if __name__ == "__main__":
    main()