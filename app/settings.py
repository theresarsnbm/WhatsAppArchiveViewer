from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

APP_DIR_NAME = "WhatsAppArchiveViewer"
SETTINGS_FILE_NAME = "settings.json"

ENV_ARCHIVE_ROOT = "WA_ARCHIVE_ROOT"


@dataclass
class Settings:
    """Dauerhaft gespeicherte Einstellungen der App."""

    archive_root: str | None = None


def config_dir() -> Path:
    """Plattformüblicher Ordner für Konfigurationsdateien."""

    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    return base / APP_DIR_NAME


def settings_path() -> Path:
    return config_dir() / SETTINGS_FILE_NAME


def default_archive_root() -> Path:
    return Path.home() / "WhatsAppArchive"


def load_settings() -> Settings:
    """Liest die Einstellungen; fehlerhafte Dateien werden ignoriert."""

    path = settings_path()

    if not path.is_file():
        return Settings()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Settings()

    archive_root = data.get("archive_root")

    if isinstance(archive_root, str) and archive_root.strip():
        return Settings(archive_root=archive_root)

    return Settings()


def save_settings(settings: Settings) -> None:
    """Schreibt die Einstellungen atomar, damit nichts halb Geschriebenes bleibt."""

    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(asdict(settings), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def get_archive_root() -> Path:
    """
    Liefert den aktuell gültigen Archivpfad.

    Reihenfolge:
    1. Umgebungsvariable WA_ARCHIVE_ROOT (für Tests und Sonderfälle)
    2. gespeicherte Einstellung
    3. Standardordner im Benutzerverzeichnis
    """

    env_value = os.environ.get(ENV_ARCHIVE_ROOT)
    if env_value:
        return Path(env_value).expanduser()

    stored = load_settings().archive_root
    if stored:
        return Path(stored).expanduser()

    return default_archive_root()


def set_archive_root(path: Path | str) -> Path:
    """Speichert einen neuen Archivpfad und legt ihn bei Bedarf an."""

    resolved = Path(str(path).strip().strip("'\"")).expanduser()

    if not resolved.is_absolute():
        raise ValueError(f"Archivpfad muss absolut sein: {resolved}")

    resolved.mkdir(parents=True, exist_ok=True)

    settings = load_settings()
    settings.archive_root = str(resolved)
    save_settings(settings)

    return resolved


def reset_archive_root() -> Path:
    """Entfernt die gespeicherte Einstellung und nutzt wieder den Standardpfad."""

    settings = load_settings()
    settings.archive_root = None
    save_settings(settings)

    return default_archive_root()


def archive_root_exists() -> bool:
    return get_archive_root().is_dir()