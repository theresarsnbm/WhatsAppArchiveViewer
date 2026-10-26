from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

APP_DIR_NAME = "WhatsAppArchiveViewer"
SETTINGS_FILE_NAME = "settings.json"

ENV_ARCHIVE_ROOT = "WA_ARCHIVE_ROOT"

DEFAULT_OWN_NAMES = ["Du"]


@dataclass
class Settings:
    """Dauerhaft gespeicherte Einstellungen der App."""

    archive_root: str | None = None
    own_names: list[str] | None = None


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
    if not isinstance(archive_root, str) or not archive_root.strip():
        archive_root = None

    own_names = data.get("own_names")
    if isinstance(own_names, list):
        own_names = [
            str(name).strip() for name in own_names if str(name).strip()
        ] or None
    else:
        own_names = None

    # Migration: altes Einzelfeld own_name übernehmen
    legacy = data.get("own_name")
    if not own_names and isinstance(legacy, str) and legacy.strip():
        own_names = [legacy.strip()]

    return Settings(archive_root=archive_root, own_names=own_names)


def save_settings(settings: Settings) -> None:
    """Schreibt die Einstellungen atomar."""

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
    1. Umgebungsvariable WA_ARCHIVE_ROOT
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


def get_own_names() -> list[str]:
    """Alle Schreibweisen, unter denen eigene Nachrichten erscheinen können."""

    names = load_settings().own_names or list(DEFAULT_OWN_NAMES)
    cleaned = [" ".join(name.split()) for name in names if name and name.strip()]

    return cleaned or list(DEFAULT_OWN_NAMES)


def set_own_names(names: list[str]) -> list[str]:
    """Speichert die eigenen Namen ohne Duplikate."""

    cleaned: list[str] = []
    seen: set[str] = set()

    for name in names:
        value = " ".join(str(name).split())

        if not value:
            continue

        key = value.casefold()
        if key in seen:
            continue

        seen.add(key)
        cleaned.append(value)

    if not cleaned:
        raise ValueError("Mindestens ein eigener Name ist erforderlich.")

    settings = load_settings()
    settings.own_names = cleaned
    save_settings(settings)

    return cleaned


def get_own_name() -> str:
    """Kompatibilität für ältere Aufrufe: erster eigener Name."""

    return get_own_names()[0]