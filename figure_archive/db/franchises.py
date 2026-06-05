import uuid
from .connection import get_connection


def create_franchise(name: str) -> str:
    conn = get_connection()
    fid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO franchises (id, name) VALUES (?, ?)",
        (fid, name.strip()),
    )
    conn.commit()
    return fid


def list_franchises() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM franchises ORDER BY sort_order, name"
    ).fetchall()
    return [dict(r) for r in rows]


def rename_franchise(fid: str, name: str) -> None:
    conn = get_connection()
    conn.execute("UPDATE franchises SET name=? WHERE id=?", (name.strip(), fid))
    conn.commit()


def delete_franchise(fid: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM franchises WHERE id=?", (fid,))
    conn.commit()
