import uuid

from figure_archive.db.connection import get_connection


def add_image(item_id: str, local_path: str,
              url: str | None = None, caption: str | None = None) -> str:
    img_id = str(uuid.uuid4())
    conn = get_connection()
    row = conn.execute(
        "SELECT COALESCE(MAX(sort_order),0)+1 FROM item_images WHERE item_id=?",
        (item_id,),
    ).fetchone()
    sort_order = row[0] if row else 1
    conn.execute(
        "INSERT INTO item_images(id,item_id,url,local_path,caption,sort_order)"
        " VALUES(?,?,?,?,?,?)",
        (img_id, item_id, url, local_path, caption, sort_order),
    )
    conn.commit()
    return img_id


def list_images(item_id: str) -> list[dict]:
    rows = get_connection().execute(
        "SELECT * FROM item_images WHERE item_id=? ORDER BY sort_order",
        (item_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def remove_image(image_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM item_images WHERE id=?", (image_id,))
    conn.commit()


def set_primary_image(item_id: str, local_path: str | None) -> None:
    conn = get_connection()
    conn.execute("UPDATE items SET primary_image=? WHERE id=?", (local_path, item_id))
    conn.commit()
