from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.config import CHATS_DIR_NAME, CHAT_FILE_NAME
from app.settings import get_archive_root

BASE_CHAT_NAMES = ("chat.txt", "_chat.txt")
VERSION_PATTERN = re.compile(r"^chat_version_(?P<number>\d+)\.txt$")
MERGED_PATTERN = re.compile(r"^merged_.*\.txt$")


@dataclass
class ChatEntry:
    folder: Path
    name: str
    media_count: int

    # ------------------------------------------------------------- Versionen

    @property
    def base_files(self) -> list[Path]:
        """chat.txt bzw. _chat.txt, falls vorhanden."""

        return [
            self.folder / filename
            for filename in BASE_CHAT_NAMES
            if (self.folder / filename).is_file()
        ]

    @property
    def numbered_version_files(self) -> list[Path]:
        """chat_version_2.txt, chat_version_3.txt … numerisch sortiert."""

        numbered: list[tuple[int, Path]] = []

        for path in self.folder.glob("chat_version_*.txt"):
            match = VERSION_PATTERN.match(path.name)
            if match and path.is_file():
                numbered.append((int(match["number"]), path))

        numbered.sort(key=lambda item: item[0])
        return [path for _, path in numbered]

    @property
    def merged_files(self) -> list[Path]:
        merged = [
            path
            for path in self.folder.glob("merged_*.txt")
            if path.is_file() and MERGED_PATTERN.match(path.name)
        ]
        return sorted(merged)

    @property
    def version_files(self) -> list[Path]:
        """Alle echten Rohversionen: chat.txt plus chat_version_N.txt."""

        return self.base_files + self.numbered_version_files

    @property
    def version_count(self) -> int:
        return len(self.version_files)

    @property
    def text_files(self) -> list[Path]:
        return self.version_files + self.merged_files

    @property
    def display_file(self) -> Path | None:
        """Bevorzugt die neueste merged_...txt, sonst die Basisdatei."""

        if self.merged_files:
            return self.merged_files[-1]

        if self.base_files:
            return self.base_files[0]

        return self.numbered_version_files[0] if self.numbered_version_files else None

    @property
    def has_merge(self) -> bool:
        return bool(self.merged_files)


def get_chats_root() -> Path:
    return get_archive_root() / CHATS_DIR_NAME


def archive_available() -> bool:
    return get_chats_root().is_dir()


def list_chats() -> list[ChatEntry]:
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
    entry = ChatEntry(
        folder=folder,
        name=read_chat_name(folder),
        media_count=count_media(folder / "Media"),
    )

    if not entry.text_files:
        return None

    return entry


def read_chat_name(folder: Path) -> str:
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
    if not media_dir.is_dir():
        return 0

    try:
        return sum(1 for path in media_dir.rglob("*") if path.is_file())
    except OSError:
        return 0


def find_chat(folder_name: str) -> ChatEntry | None:
    target = folder_name.casefold()

    for entry in list_chats():
        if entry.folder.name.casefold() == target or entry.name.casefold() == target:
            return entry

    return None