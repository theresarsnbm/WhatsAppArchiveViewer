from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.config import CHAT_FILE_NAME
from app.parser import parse_chat_file, Message, normalize_sender
from app.settings import get_own_names


@dataclass
class MergeResult:
    merged_file: Path
    version_files: list[Path]
    total_messages: int
    unique_messages: int
    duplicates_removed: int


class MergeError(Exception):
    """Wird ausgelöst, wenn nicht gemergt werden kann."""


def merge_chat_versions(chat_dir: Path, own_names=None) -> MergeResult:
    """Fasst alle Textversionen eines Chat-Ordners zu einer merged_...txt zusammen."""

    own_names = own_names or get_own_names()
    version_files = collect_chat_files(chat_dir)

    if len(version_files) < 2:
        raise MergeError(
            f"Im Ordner {chat_dir.name} liegt nur eine Chat-Version. "
            "Für einen Merge werden mindestens zwei benötigt."
        )

    all_messages: list[Message] = []

    for chat_file in version_files:
        all_messages.extend(parse_chat_file(chat_file, own_names=own_names))

    total_messages = len(all_messages)
    unique = deduplicate_messages(all_messages)
    unique.sort(key=lambda message: message.timestamp)

    merged_file = next_merged_path(chat_dir)
    write_merged_chat_file(merged_file, unique)

    return MergeResult(
        merged_file=merged_file,
        version_files=version_files,
        total_messages=total_messages,
        unique_messages=len(unique),
        duplicates_removed=total_messages - len(unique),
    )


def collect_chat_files(chat_dir: Path) -> list[Path]:
    """Sammelt chat.txt und alle chat_version_N.txt in aufsteigender Reihenfolge."""

    files: list[Path] = []

    base_file = chat_dir / CHAT_FILE_NAME
    if base_file.is_file():
        files.append(base_file)

    versioned = sorted(
        chat_dir.glob("chat_version_*.txt"),
        key=version_number,
    )
    files.extend(versioned)

    return files


def version_number(path: Path) -> int:
    """Sortiert chat_version_2.txt vor chat_version_10.txt."""

    stem = path.stem
    suffix = stem.removeprefix("chat_version_")

    return int(suffix) if suffix.isdigit() else 0


def deduplicate_messages(messages: list[Message]) -> list[Message]:
    """
    Entfernt Nachrichten, die in mehreren Exporten identisch vorkommen.

    Identisch heißt: gleicher Zeitstempel, gleicher Absender,
    gleicher Text und gleiche Anhangsdateinamen.
    """

    seen: set[tuple] = set()
    unique: list[Message] = []

    for message in messages:
        key = message_key(message)

        if key in seen:
            continue

        seen.add(key)
        unique.append(message)

    return unique


def message_key(message: Message) -> tuple:
    normalized_text = " ".join(message.text.casefold().split())
    attachment_names = tuple(
        sorted(attachment.filename.casefold() for attachment in message.attachments)
    )

    # Eigene Nachrichten unabhängig von der Schreibweise als "self" behandeln
    sender_key = "self" if message.is_own_message else normalize_sender(message.sender)

    return (message.timestamp, sender_key, normalized_text, attachment_names)


def next_merged_path(chat_dir: Path) -> Path:
    """Erzeugt einen eindeutigen Dateinamen mit aktuchem Zeitstempel."""

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    candidate = chat_dir / f"merged_{timestamp}.txt"

    counter = 2
    while candidate.exists():
        candidate = chat_dir / f"merged_{timestamp}_{counter}.txt"
        counter += 1

    return candidate


def write_merged_chat_file(target: Path, messages: list[Message]) -> None:
    """Schreibt die Nachrichten im WhatsApp-Exportformat."""

    with target.open("w", encoding="utf-8", newline="\n") as file:
        for message in messages:
            timestamp = message.timestamp.strftime("%d.%m.%y, %H:%M:%S")
            file.write(f"[{timestamp}] {message.sender}: {message.text}\n")

            for attachment in message.attachments:
                file.write(f"<Anhang: {attachment.filename}>\n")