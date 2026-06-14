import uuid
from .connection import get_connection


def create_wave(line_id: str, name: str, year: int | None = None,
                sort_order: int = 0, parent_id: str | None = None) -> str:
    conn = get_connection()
    wid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO waves (id, line_id, parent_id, name, year, sort_order)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (wid, line_id, parent_id, name.strip(), year, sort_order),
    )
    conn.commit()
    return wid


def list_waves(line_id: str) -> list[dict]:
    """Flat list of all groups for a line, ordered by sort_order/name."""
    rows = get_connection().execute(
        "SELECT * FROM waves WHERE line_id=? ORDER BY sort_order, name",
        (line_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_groups_tree(line_id: str) -> list[dict]:
    """Return groups depth-first with a 'depth' key added.

    Each dict has all wave columns plus:
      depth (int)  — 0 for root groups, 1 for children, etc.
      children     — list of child dicts (same structure, for recursion)
    """
    all_groups = list_waves(line_id)
    by_id = {g["id"]: dict(g, depth=0, children=[]) for g in all_groups}
    roots: list[dict] = []
    for g in by_id.values():
        pid = g.get("parent_id")
        if pid and pid in by_id:
            by_id[pid]["children"].append(g)
        else:
            roots.append(g)

    def _flatten(nodes: list[dict], depth: int) -> list[dict]:
        result = []
        for n in sorted(nodes, key=lambda x: (x.get("sort_order") or 0, x["name"])):
            n["depth"] = depth
            result.append(n)
            result.extend(_flatten(n["children"], depth + 1))
        return result

    return _flatten(roots, 0)


def get_wave(wid: str) -> dict | None:
    row = get_connection().execute(
        "SELECT * FROM waves WHERE id=?", (wid,)
    ).fetchone()
    return dict(row) if row else None


def rename_wave(wid: str, name: str) -> None:
    conn = get_connection()
    conn.execute("UPDATE waves SET name=? WHERE id=?", (name.strip(), wid))
    conn.commit()


def delete_wave(wid: str) -> None:
    """Delete a group; its items fall back to no-group, children become roots."""
    conn = get_connection()
    conn.execute("UPDATE items SET wave_id=NULL WHERE wave_id=?", (wid,))
    conn.execute("UPDATE waves SET parent_id=NULL WHERE parent_id=?", (wid,))
    conn.execute("DELETE FROM waves WHERE id=?", (wid,))
    conn.commit()
