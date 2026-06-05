import uuid
from .connection import get_connection


def create_line(franchise_id: str, name: str, type_plugin_id: str = "generic") -> str:
    conn = get_connection()
    lid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO lines (id, franchise_id, name, type_plugin_id) VALUES (?, ?, ?, ?)",
        (lid, franchise_id, name.strip(), type_plugin_id),
    )
    conn.commit()
    return lid


def list_lines(franchise_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM lines WHERE franchise_id=? ORDER BY sort_order, name",
        (franchise_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def rename_line(lid: str, name: str) -> None:
    conn = get_connection()
    conn.execute("UPDATE lines SET name=? WHERE id=?", (name.strip(), lid))
    conn.commit()


def delete_line(lid: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM lines WHERE id=?", (lid,))
    conn.commit()
