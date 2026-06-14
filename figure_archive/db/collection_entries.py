import uuid
from datetime import datetime, timezone
from .connection import get_connection

# Ownership status values
NOT_OWNED = 0
OWNED = 1
SOLD = 2
WANTED = 3
ON_ORDER = 4

# Wishlist priority values
WATCHING = 0
WISH_WANTED = 1
GRAIL = 2

_UPDATABLE = {
    "owned", "wishlist_priority", "quantity", "condition", "box_condition",
    "packaging_state", "completeness", "is_complete", "missing_accessories",
    "acquired_date", "paid_price", "acquired_from", "estimated_value",
    "personal_rating", "is_favorite", "on_display", "needs_repair",
    "is_loaned", "loaned_to", "is_for_sale", "is_sealed", "personal_notes",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_or_create_entry(item_id: str) -> dict:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM collection_entries WHERE item_id=?", (item_id,)
    ).fetchone()
    if row:
        return dict(row)
    eid = str(uuid.uuid4())
    now = _now()
    conn.execute(
        "INSERT INTO collection_entries (id, item_id, created_at, updated_at) "
        "VALUES (?, ?, ?, ?)",
        (eid, item_id, now, now),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM collection_entries WHERE item_id=?", (item_id,)
    ).fetchone()
    return dict(row)


def set_owned(item_id: str, status: int) -> None:
    update_entry(item_id, owned=status)


def update_entry(item_id: str, **fields) -> None:
    get_or_create_entry(item_id)
    fields = {k: v for k, v in fields.items() if k in _UPDATABLE}
    if not fields:
        return
    fields["updated_at"] = _now()
    conn = get_connection()
    cols = ", ".join(f"{k}=?" for k in fields)
    conn.execute(
        f"UPDATE collection_entries SET {cols} WHERE item_id=?",
        (*fields.values(), item_id),
    )
    conn.commit()
