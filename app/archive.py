from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import CHATS_DIR_NAME, CHAT_FILE_NAME
from app.settings import get_archive_root


@dataclass
class ChatEntry:
    """Ein Chat im Archiv: ein Ordner mit Textversionen und einem Media-Ordner."""

    folder: Path
    name: str
    text_files: list[Path]
    media_count: int

    @property
    def display_file(self) -> Path | None:
        """
        Bevorzugt die neueste merged_...txt, sonst chat.txt.

        Die merged-Dateien heißen merged_YYYY-MM-DD_HH-MM-SS.txt,
        daher genügt alphabetisches Sortieren.
        """

        merged = sorted(self.folder.glob("merged_*.txt"))
        if merged:
            return merged[-1]

        for filename in (CHAT_FILE_NAME, "_chat.txt"):
            candidate = self.folder / filename
            if candidate.is_file():
                return candidate

        return self.text_files[0] if self.text_files else None

    @property
    def version_files(self) -> list[Path]:
        """Alle nicht gemergten Textversionen."""

        return [
            path
            for path in self.text_files
            if not path.name.startswith("merged_")
        ]

    @property
    def version_count(self) -> int:
        return len(self.version_files)

    @property
    def has_merge(self) -> bool:
        return any(path.name.startswith("merged_") for path in self.text_files)


def get_chats_root() -> Path:
    """Aktueller Chat-Ordner innerhalb des konfigurierten Archivs."""

    return get_archive_root() / CHATS_DIR_NAME


def archive_available() -> bool:
    return get_chats_root().is_dir()


def list_chats() -> list[ChatEntry]:
    """Liest alle Chat-Ordner aus dem Archiv."""

    chats_root = get_chats_root()

    if not chats_root.is_dir():
        return []

    entries: list[ChatEntry] = []

    try:
        folders = sorted(chats_root.iterdir())
    except OSError:
        return []

    for folder in folders:
        if not folder.is_dir():
            continue

        entry = build_chat_entry(folder)
        if entry is not None:
            entries.append(entry)

    entries.sort(key=lambda entry: entry.name.casefold())
    return entries


def build_chat_entry(folder: Path) -> ChatEntry | None:
    """Baut einen ChatEntry; Ordner ohne Textdatei werden übersprungen."""

    text_files = sorted(folder.glob("chat*.txt")) + sorted(folder.glob("merged_*.txt"))

    if not text_files:
        return None

    return ChatEntry(
        folder=folder,
        name=read_chat_name(folder),
        text_files=text_files,
        media_count=count_media(folder / "Media"),
    )


def read_chat_name(folder: Path) -> str:
    """Liest den ursprünglichen Chatnamen, sonst den Ordnernamen."""

    chat_name_file = folder / "chat_name.txt"

    if chat_name_file.is_file():
        try:
            stored = chat_name_file.read_text(encoding="utf-8").strip()
        except OSError:
            stored = ""

        if stored:
            return stored

    return folder.name


def count_media(media_dir: Path) -> int:
    """Zählt Mediendateien im Media-Ordner des Chats."""

    if not media_dir.is_dir():
        return 0

    try:
        return sum(1 for path in media_dir.rglob("*") if path.is_file())
    except OSError:
        return 0


def find_chat(folder_name: str) -> ChatEntry | None:
    """Sucht einen Chat unabhängig von Groß-/Kleinschreibung."""

    target = folder_name.casefold()

    for entry in list_chats():
        if entry.folder.name.casefold() == target or entry.name.casefold() == target:
            return entry

    return None