from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from app.models import Attachment, Message

# Beispiel: [05.12.24, 10:18:05] Theresa Rosenbaum: Text
MESSAGE_START = re.compile(
    r"^\[(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{2}), "
    r"(?P<time>\d{2}:\d{2}:\d{2})\] "
    r"(?P<sender>.+?): "
    r"(?P<body>.*)$"
)

# Beispiel: <Anhang: 00000002-PHOTO-2024-12-05-10-18-05.jpg>
ATTACHMENT = re.compile(r"<Anhang:\s*(?P<filename>.+?)>")

# Unsichtbare Steuerzeichen, die WhatsApp-Exporte enthalten
INVISIBLE_CHARS = {"\u200e", "\u200f", "\ufeff"}

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".gif", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".3gp"}
AUDIO_SUFFIXES = {".opus", ".mp3", ".m4a", ".wav", ".aac", ".ogg"}
DOCUMENT_SUFFIXES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}


def clean_text(value: str) -> str:
    """Entfernt unsichtbare Zeichen und Rand-Leerzeichen."""

    for char in INVISIBLE_CHARS:
        value = value.replace(char, "")

    return value.strip()


def detect_kind(filename: str) -> str:
    """Bestimmt den Medientyp anhand der Dateiendung."""

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


def parse_chat_file(chat_path: Path) -> list[Message]:
    """
    Liest eine WhatsApp-Textdatei und gibt alle Nachrichten zurück.

    Mehrzeilige Nachrichten werden korrekt zusammengeführt:
    Eine neue Nachricht beginnt erst wieder mit einem Zeitstempel.
    """

    if not chat_path.is_file():
        raise FileNotFoundError(f"Chat-Datei nicht gefunden: {chat_path}")

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

                current = Message(
                    timestamp=timestamp,
                    sender=match["sender"].strip(),
                    text="",
                    source_file=chat_path,
                )
                body = match["body"]
            else:
                if current is None:
                    # Zeilen vor der ersten Nachricht ignorieren
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
    """Sucht Anhangsverweise im Nachrichtentext und ordnet Dateien zu."""

    attachments: list[Attachment] = []

    for match in ATTACHMENT.finditer(text):
        filename = match["filename"].strip()
        path = find_media_file(filename, chat_dir)

        attachments.append(
            Attachment(
                filename=filename,
                path=path,
                kind=detect_kind(filename),
            )
        )

    return attachments


def find_media_file(filename: str, chat_dir: Path) -> Path | None:
    """
    Sucht eine Mediendatei im Chat-Ordner.

    Reihenfolge entspricht der Archivstruktur:
    Media/ -> media/ -> direkt im Chat-Ordner
    """

    candidates = [
        chat_dir / "Media" / filename,
        chat_dir / "media" / filename,
        chat_dir / filename,
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    # Sicherheitsnetz: irgendwo im Chat-Ordner suchen
    try:
        return next(chat_dir.rglob(filename), None)
    except OSError:
        return None