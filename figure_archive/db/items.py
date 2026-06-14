import uuid
from .connection import get_connection

# Columns on the items table that may be updated via update_item()
_UPDATABLE = {
    "name", "item_type", "year", "manufacturer", "scale", "upc",
    "description", "accessories", "wave_id", "sort_order", "primary_image",
}


def create_item(line_id: str, name: str, item_type: str = "figure",
                wave_id: str | None = None, **fields) -> str:
    conn = get_connection()
    iid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO items (id, line_id, name, item_type, wave_id) VALUES (?, ?, ?, ?, ?)",
        (iid, line_id, name.strip(), item_type, wave_id),
    )
    conn.commit()
    if fields:
        update_item(iid, **fields)
    return iid


def get_item(item_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    return dict(row) if row else None


def list_items(line_id: str) -> list[dict]:
    """All items in a line, with their collection_entry fields joined in."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT i.*,
               ce.owned, ce.wishlist_priority, ce.condition, ce.is_favorite,
               ce.on_display, ce.needs_repair, ce.personal_rating
        FROM items i
        LEFT JOIN collection_entries ce ON ce.item_id = i.id
        WHERE i.line_id = ?
        ORDER BY i.sort_order, i.name
        """,
        (line_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def update_item(item_id: str, **fields) -> None:
    fields = {k: v for k, v in fields.items() if k in _UPDATABLE}
    if not fields:
        return
    conn = get_connection()
    cols = ", ".join(f"{k}=?" for k in fields)
    conn.execute(
        f"UPDATE items SET {cols} WHERE id=?",
        (*fields.values(), item_id),
    )
    conn.commit()


def delete_item(item_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
