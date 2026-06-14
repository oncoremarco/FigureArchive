import uuid
from datetime import datetime

from figure_archive.db.connection import get_connection


def add_photo(item_id: str, local_path: str, caption: str | None = None) -> str:
    photo_id = str(uuid.uuid4())
    conn = get_connection()
    row = conn.execute(
        "SELECT COALESCE(MAX(sort_order),0)+1 FROM personal_photos WHERE item_id=?",
        (item_id,),
    ).fetchone()
    sort_order = row[0] if row else 1
    conn.execute(
        "INSERT INTO personal_photos(id,item_id,local_path,caption,sort_order,added_at)"
        " VALUES(?,?,?,?,?,?)",
        (photo_id, item_id, local_path, caption, sort_order, datetime.utcnow().isoformat()),
    )
    conn.commit()
    return photo_id


def list_photos(item_id: str) -> list[dict]:
    rows = get_connection().execute(
        "SELECT * FROM personal_photos WHERE item_id=? ORDER BY sort_order",
        (item_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def remove_photo(photo_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM personal_photos WHERE id=?", (photo_id,))
    conn.commit()
