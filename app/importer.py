from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.config import (
    ARCHIVE_ROOT,
    CHAT_FILE_NAME,
    CHATS_DIR_NAME,
    MEDIA_DIR_NAME,
)
from app.merger import MergeError, MergeResult, merge_chat_versions

CHAT_FILE_NAMES = {"chat.txt", "_chat.txt"}
IGNORED_SUFFIXES = {".zip", ".txt"}


class ImporterError(Exception):
    """Wird ausgelöst, wenn ein Export nicht importiert werden kann."""


@dataclass
class ImportResult:
    chat_dir: Path
    imported_file: Path
    version_count: int
    merge_result: MergeResult | None

    @property
    def merged_file(self) -> Path | None:
        return self.merge_result.merged_file if self.merge_result else None


def import_chat_export(export_dir: Path | str, chat_name: str) -> ImportResult:
    """
    Importiert einen entpackten WhatsApp-Export in das lokale Archiv.

    Liegt danach mehr als eine Textversion vor, wird automatisch
    eine merged_...txt erzeugt.
    """

    export_dir = Path(str(export_dir).strip().strip("'\"")).expanduser()

    if not export_dir.is_dir():
        raise ImporterError(f"Export-Ordner nicht gefunden: {export_dir}")

    archive_root = Path(ARCHIVE_ROOT).expanduser()
    if export_dir.resolve().is_relative_to(archive_root.resolve()):
        raise ImporterError(
            "Der Export-Ordner liegt innerhalb des Archivs. "
            "Bitte den ursprünglichen WhatsApp-Export wählen."
        )

    chat_file = find_chat_file(export_dir)
    if chat_file is None:
        raise ImporterError(
            f"Keine {CHAT_FILE_NAME} oder _chat.txt in {export_dir} gefunden."
        )

    chats_root = archive_root / CHATS_DIR_NAME
    chats_root.mkdir(parents=True, exist_ok=True)

    chat_dir = get_or_create_chat_dir(chats_root, chat_name)
    target_chat_file = next_chat_version_path(chat_dir)

    shutil.copy2(chat_file, target_chat_file)

    import_media_files(
        export_dir=export_dir,
        chat_file=chat_file,
        target_media_dir=chat_dir / MEDIA_DIR_NAME,
    )

    version_count = count_existing_versions(chat_dir)
    merge_result = merge_if_possible(chat_dir, version_count)

    return ImportResult(
        chat_dir=chat_dir,
        imported_file=target_chat_file,
        version_count=version_count,
        merge_result=merge_result,
    )


def merge_if_possible(chat_dir: Path, version_count: int) -> MergeResult | None:
    """Mergt automatisch, sobald mindestens zwei Versionen existieren."""

    if version_count < 2:
        return None

    try:
        return merge_chat_versions(chat_dir)
    except MergeError:
        return None


def find_chat_file(export_dir: Path) -> Path | None:
    """Sucht die WhatsApp-Textdatei direkt im Export-Ordner."""

    for name in CHAT_FILE_NAMES:
        candidate = export_dir / name
        if candidate.is_file():
            return candidate

    for candidate in export_dir.glob("*.txt"):
        if candidate.is_file():
            return candidate

    return None


def next_chat_version_path(chat_dir: Path) -> Path:
    """
    Liefert den nächsten freien Dateinamen für eine Chat-Version.

    chat.txt existiert bereits? -> chat_version_2.txt
    auch die?                  -> chat_version_3.txt usw.
    """

    base_file = chat_dir / CHAT_FILE_NAME

    if not base_file.exists():
        return base_file

    version = 2

    while True:
        candidate = chat_dir / f"chat_version_{version}.txt"
        if not candidate.exists():
            return candidate
        version += 1


def import_media_files(
    export_dir: Path,
    chat_file: Path,
    target_media_dir: Path,
) -> None:
    """Kopiert neue Medien in den einen Media-Ordner des Chats."""

    target_media_dir.mkdir(parents=True, exist_ok=True)

    for source_file in iter_media_candidates(export_dir, chat_file):
        relative_path = source_file.relative_to(export_dir)

        if relative_path.parts and relative_path.parts[0].lower() == "media":
            relative_path = Path(*relative_path.parts[1:])

        target_file = target_media_dir / relative_path

        if target_file.exists():
            continue

        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_file)


def iter_media_candidates(export_dir: Path, chat_file: Path):
    """Liefert alle Dateien, die als Medien importiert werden sollen."""

    for path in export_dir.rglob("*"):
        if not path.is_file():
            continue

        if path == chat_file:
            continue

        if path.name in CHAT_FILE_NAMES:
            continue

        if path.name.startswith("."):
            continue

        if "__MACOSX" in path.parts:
            continue

        if path.suffix.lower() in IGNORED_SUFFIXES:
            continue

        yield path


def get_or_create_chat_dir(chats_root: Path, chat_name: str) -> Path:
    """Nutzt den eingegebenen Chatnamen als Ordnernamen."""

    folder_name = safe_folder_name(chat_name)
    if not folder_name:
        raise ImporterError(f"Ungültiger Chatname: {chat_name!r}")

    chat_dir = chats_root / folder_name

    if chat_dir.is_dir():
        return chat_dir

    chat_dir.mkdir(parents=True)

    chat_name_file = chat_dir / "chat_name.txt"
    chat_name_file.write_text(chat_name.strip(), encoding="utf-8")

    return chat_dir


def safe_folder_name(chat_name: str) -> str:
    """Macht aus einem Chatnamen einen gültigen Ordnernamen."""

    name = chat_name.strip()
    name = re.sub(r"[/:\\]", "-", name)
    name = name.strip(". ")

    return name


def count_existing_versions(chat_dir: Path) -> int:
    """Zählt chat.txt plus alle chat_version_-Dateien."""

    count = 0

    if (chat_dir / CHAT_FILE_NAME).is_file():
        count += 1

    count += sum(
        1
        for path in chat_dir.glob("chat_version_*.txt")
        if path.is_file()
    )

    return count