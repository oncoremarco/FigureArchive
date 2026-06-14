import uuid
from .connection import get_connection


def create_wave(line_id: str, name: str, year: int | None = None,
                 sort_order: int = 0) -> str:
    conn = get_connection()
    wid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO waves (id, line_id, name, year, sort_order) VALUES (?, ?, ?, ?, ?)",
        (wid, line_id, name.strip(), year, sort_order),
    )
    conn.commit()
    return wid


def list_waves(line_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM waves WHERE line_id=? ORDER BY sort_order, name",
        (line_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def rename_wave(wid: str, name: str) -> None:
    conn = get_connection()
    conn.execute("UPDATE waves SET name=? WHERE id=?", (name.strip(), wid))
    conn.commit()


def delete_wave(wid: str) -> None:
    # Items in this wave fall back to "no wave" (wave_id set null)
    conn = get_connection()
    conn.execute("UPDATE items SET wave_id=NULL WHERE wave_id=?", (wid,))
    conn.execute("DELETE FROM waves WHERE id=?", (wid,))
    conn.commit()
