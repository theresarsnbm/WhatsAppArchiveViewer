from __future__ import annotations

import shutil
from pathlib import Path

from app.config import (
    ARCHIVE_ROOT,
    CHAT_FILE_NAME,
    CHATS_DIR_NAME,
    MEDIA_DIR_NAME,
)

CHAT_FILE_NAMES = {"chat.txt", "_chat.txt"}
IGNORED_SUFFIXES = {".zip", ".txt"}


class ImporterError(Exception):
    """Wird ausgelöst, wenn ein Export nicht importiert werden kann."""


def import_chat_export(export_dir: Path | str, chat_name: str) -> Path:
    """
    Importiert einen entpackten WhatsApp-Export in das lokale Archiv.

    Unterstützt flache Exporte (chat.txt und Medien auf einer Ebene)
    sowie Exporte mit Media/-Unterordner.
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
    version_number = count_existing_versions(chat_dir)

    if version_number == 0:
        target_chat_file = chat_dir / CHAT_FILE_NAME
    else:
        target_chat_file = chat_dir / f"chat_version_{version_number + 1}.txt"

    shutil.copy2(chat_file, target_chat_file)

    import_media_files(
        export_dir=export_dir,
        chat_file=chat_file,
        target_media_dir=chat_dir / MEDIA_DIR_NAME,
    )

    return chat_dir


def find_chat_file(export_dir: Path) -> Path | None:
    """Sucht die WhatsApp-Textdatei direkt im Export-Ordner."""

    for name in CHAT_FILE_NAMES:
        candidate = export_dir / name
        if candidate.is_file():
            return candidate

    # Fallback: irgendeine .txt direkt im Export-Ordner
    for candidate in export_dir.glob("*.txt"):
        if candidate.is_file():
            return candidate

    return None


def import_media_files(
    export_dir: Path,
    chat_file: Path,
    target_media_dir: Path,
) -> None:
    """
    Kopiert alle Mediendateien aus dem Export in den einen Media-Ordner.

    Vorhandene Dateien werden nicht überschrieben.
    """

    target_media_dir.mkdir(parents=True, exist_ok=True)

    for source_file in iter_media_candidates(export_dir, chat_file):
        relative_path = source_file.relative_to(export_dir)

        # Media/, media/ usw. als oberste Ebene entfernen
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
    """Findet einen bestehenden Chat oder legt einen neuen an."""

    existing_chat_dir = find_existing_chat_dir(chats_root, chat_name)
    if existing_chat_dir is not None:
        return existing_chat_dir

    next_id = get_next_chat_id(chats_root)
    chat_dir = chats_root / f"chat_{next_id}"
    chat_dir.mkdir(parents=True, exist_ok=True)

    chat_name_file = chat_dir / "chat_name.txt"
    chat_name_file.write_text(chat_name, encoding="utf-8")

    return chat_dir


def find_existing_chat_dir(chats_root: Path, chat_name: str) -> Path | None:
    """Vergleicht Chatnamen unabhängig von Groß-/Kleinschreibung."""

    normalized_input = normalize_chat_name(chat_name)

    for chat_dir in chats_root.iterdir():
        if not chat_dir.is_dir():
            continue

        chat_name_file = chat_dir / "chat_name.txt"
        if not chat_name_file.is_file():
            continue

        stored_name = chat_name_file.read_text(encoding="utf-8").strip()

        if normalize_chat_name(stored_name) == normalized_input:
            return chat_dir

    return None


def normalize_chat_name(value: str) -> str:
    """Macht 'Theresa Rosenbaum' und 'theresa rosenbaum' vergleichbar."""

    return " ".join(value.casefold().split())


def get_next_chat_id(chats_root: Path) -> int:
    """Ermittelt die nächste freie chat_-Nummer."""

    highest_id = 0

    for chat_dir in chats_root.iterdir():
        if not chat_dir.is_dir():
            continue

        if not chat_dir.name.startswith("chat_"):
            continue

        suffix = chat_dir.name.removeprefix("chat_")

        if suffix.isdigit():
            highest_id = max(highest_id, int(suffix))

    return highest_id + 1


def count_existing_versions(chat_dir: Path) -> int:
    """Zählt vorhandene chat_version_-Dateien."""

    count = 0

    for path in chat_dir.iterdir():
        if path.is_file() and path.name.startswith("chat_version_"):
            count += 1

    return count