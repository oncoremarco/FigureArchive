import sqlite3
from pathlib import Path

_connection: sqlite3.Connection | None = None
_current_path: Path | None = None


def open_collection(db_path: str | Path) -> sqlite3.Connection:
    global _connection, _current_path
    if _connection:
        _connection.close()
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.commit()
    _connection = conn
    _current_path = path
    return conn


def get_connection() -> sqlite3.Connection:
    if _connection is None:
        raise RuntimeError("No collection is open. Call open_collection() first.")
    return _connection


def close_collection() -> None:
    global _connection, _current_path
    if _connection:
        _connection.close()
    _connection = None
    _current_path = None


def current_path() -> Path | None:
    return _current_path
