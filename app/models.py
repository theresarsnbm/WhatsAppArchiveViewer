from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Attachment:
    """Eine Mediendatei, die in einer Nachricht referenziert wird."""

    filename: str
    path: Path | None
    kind: str

    @property
    def exists(self) -> bool:
        return self.path is not None and self.path.is_file()


@dataclass
class Message:
    """Eine einzelne Chat-Nachricht."""

    timestamp: datetime
    sender: str
    text: str
    source_file: Path
    attachments: list[Attachment] = field(default_factory=list)

    @property
    def is_own_message(self) -> bool:
        return self.sender == "Du"

    @property
    def has_media(self) -> bool:
        return bool(self.attachments)