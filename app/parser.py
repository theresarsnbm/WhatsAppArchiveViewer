from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

MESSAGE_START = re.compile(
    r"^\[(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{2}), "
    r"(?P<time>\d{2}:\d{2}:\d{2})\] "
    r"(?P<sender>.+?): "
    r"(?P<body>.*)$"
)

ATTACHMENT = re.compile(r"<Anhang:\s*(?P<filename>.+?)>")

INVISIBLE_CHARS = {"\u200e", "\u200f", "\ufeff"}

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".gif", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".3gp"}
AUDIO_SUFFIXES = {".opus", ".mp3", ".m4a", ".wav", ".aac", ".ogg"}
DOCUMENT_SUFFIXES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}


@dataclass
class Attachment:
    filename: str
    path: Path | None
    kind: str

    @property
    def exists(self) -> bool:
        return self.path is not None and self.path.is_file()


@dataclass
class Message:
    timestamp: datetime
    sender: str
    text: str
    source_file: Path
    attachments: list[Attachment] = field(default_factory=list)
    is_own: bool = False

    @property
    def is_own_message(self) -> bool:
        return self.is_own

    @property
    def has_media(self) -> bool:
        return bool(self.attachments)


def clean_text(value: str) -> str:
    for char in INVISIBLE_CHARS:
        value = value.replace(char, "")

    return value.strip()


def normalize_sender(value: str) -> str:
    """Absendernamen vergleichbar machen: Leerzeichen und Groß-/Kleinschreibung."""

    return " ".join(value.split()).casefold()


def build_own_name_set(
    own_names: str | list[str] | tuple[str, ...] | None,
) -> set[str]:
    """Erzeugt die Menge aller Schreibweisen eigener Nachrichten."""

    if own_names is None:
        values = ["Du"]
    elif isinstance(own_names, str):
        values = [own_names]
    else:
        values = list(own_names)

    normalized = {
        normalize_sender(value) for value in values if value and value.strip()
    }
    normalized.add("du")

    return normalized


def detect_kind(filename: str) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    if suffix in AUDIO_SUFFIXES:
        return "audio"
    if suffix in DOCUMENT_SUFFIXES:
        return "document"

    return "file"


def parse_chat_file(
    chat_path: Path,
    own_names: str | list[str] | tuple[str, ...] | None = None,
) -> list[Message]:
    if not chat_path.is_file():
        raise FileNotFoundError(f"Chat-Datei nicht gefunden: {chat_path}")

    own_set = build_own_name_set(own_names)
    messages: list[Message] = []
    current: Message | None = None

    with chat_path.open("r", encoding="utf-8", errors="replace") as file:
        for raw_line in file:
            line = clean_text(raw_line.rstrip("\r\n"))
            match = MESSAGE_START.match(line)

            if match:
                if current is not None:
                    messages.append(current)

                timestamp = datetime.strptime(
                    f"{match['day']}.{match['month']}.{match['year']} "
                    f"{match['time']}",
                    "%d.%m.%y %H:%M:%S",
                )
                sender = match["sender"].strip()

                current = Message(
                    timestamp=timestamp,
                    sender=sender,
                    text="",
                    source_file=chat_path,
                    is_own=normalize_sender(sender) in own_set,
                )
                body = match["body"]
            else:
                if current is None:
                    continue
                body = line

            if body:
                current.text = f"{current.text}\n{body}" if current.text else body

    if current is not None:
        messages.append(current)

    for message in messages:
        message.attachments = extract_attachments(message.text, chat_path.parent)
        message.text = clean_text(ATTACHMENT.sub("", message.text))

    return messages


def extract_attachments(text: str, chat_dir: Path) -> list[Attachment]:
    attachments: list[Attachment] = []

    for match in ATTACHMENT.finditer(text):
        filename = match["filename"].strip()
        path = find_media_file(filename, chat_dir)

        attachments.append(
            Attachment(filename=filename, path=path, kind=detect_kind(filename))
        )

    return attachments


def find_media_file(filename: str, chat_dir: Path) -> Path | None:
    candidates = [
        chat_dir / "Media" / filename,
        chat_dir / "media" / filename,
        chat_dir / filename,
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    try:
        return next(chat_dir.rglob(filename), None)
    except OSError:
        return None