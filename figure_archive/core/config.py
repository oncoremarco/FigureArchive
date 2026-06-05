import json
import os
import sys
from pathlib import Path


def _app_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "FigureArchive"


_APP_DATA = _app_data_dir()
_CONFIG_FILE = _APP_DATA / "config.json"
_data: dict = {}


def load() -> None:
    _APP_DATA.mkdir(parents=True, exist_ok=True)
    collections_dir().mkdir(parents=True, exist_ok=True)
    global _data
    if _CONFIG_FILE.exists():
        try:
            _data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            _data = {}
    else:
        _data = {}


def save() -> None:
    _APP_DATA.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(_data, indent=2), encoding="utf-8")


def get(key: str, default=None):
    return _data.get(key, default)


def set(key: str, value) -> None:
    _data[key] = value
    save()


def app_data_dir() -> Path:
    return _APP_DATA


def collections_dir() -> Path:
    return _APP_DATA / "collections"
