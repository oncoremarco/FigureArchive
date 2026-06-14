import uuid
from .connection import get_connection


def create_tag(name: str, color: str = "#89b4fa") -> str:
    conn = get_connection()
    tid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO tags (id, name, color) VALUES (?, ?, ?)",
        (tid, name.strip(), color),
    )
    conn.commit()
    return tid


def list_tags() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tags ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def rename_tag(tag_id: str, name: str, color: str | None = None) -> None:
    conn = get_connection()
    if color is not None:
        conn.execute(
            "UPDATE tags SET name=?, color=? WHERE id=?",
            (name.strip(), color, tag_id),
        )
    else:
        conn.execute("UPDATE tags SET name=? WHERE id=?", (name.strip(), tag_id))
    conn.commit()


def delete_tag(tag_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM tags WHERE id=?", (tag_id,))
    conn.commit()


def add_tag_to_item(item_id: str, tag_id: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO item_tags (item_id, tag_id) VALUES (?, ?)",
        (item_id, tag_id),
    )
    conn.commit()


def remove_tag_from_item(item_id: str, tag_id: str) -> None:
    conn = get_connection()
    conn.execute(
        "DELETE FROM item_tags WHERE item_id=? AND tag_id=?",
        (item_id, tag_id),
    )
    conn.commit()


def list_tags_for_item(item_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT t.* FROM tags t
        JOIN item_tags it ON it.tag_id = t.id
        WHERE it.item_id = ?
        ORDER BY t.name
        """,
        (item_id,),
    ).fetchall()
    return [dict(r) for r in rows]
