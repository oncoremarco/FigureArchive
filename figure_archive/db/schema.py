import sqlite3

_TABLES = """
CREATE TABLE IF NOT EXISTS sources (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    last_used   TEXT
);

CREATE TABLE IF NOT EXISTS franchises (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    source_id   TEXT,
    source_key  TEXT,
    sort_order  INTEGER DEFAULT 0,
    notes       TEXT,
    banner_image TEXT
);

CREATE TABLE IF NOT EXISTS lines (
    id              TEXT PRIMARY KEY,
    franchise_id    TEXT NOT NULL REFERENCES franchises(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    year_start      INTEGER,
    year_end        INTEGER,
    manufacturer    TEXT,
    source_id       TEXT,
    source_key      TEXT,
    sort_order      INTEGER DEFAULT 0,
    notes           TEXT,
    thumbnail       TEXT,
    type_plugin_id  TEXT DEFAULT 'generic'
);

CREATE TABLE IF NOT EXISTS waves (
    id          TEXT PRIMARY KEY,
    line_id     TEXT NOT NULL REFERENCES lines(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    year        INTEGER,
    sort_order  INTEGER DEFAULT 0,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS items (
    id              TEXT PRIMARY KEY,
    line_id         TEXT NOT NULL REFERENCES lines(id) ON DELETE CASCADE,
    wave_id         TEXT REFERENCES waves(id),
    name            TEXT NOT NULL,
    item_type       TEXT NOT NULL DEFAULT 'figure',
    year            INTEGER,
    manufacturer    TEXT,
    scale           TEXT,
    upc             TEXT,
    description     TEXT,
    accessories     TEXT,
    source_id       TEXT,
    source_key      TEXT,
    source_url      TEXT,
    sort_order      INTEGER DEFAULT 0,
    primary_image   TEXT,
    UNIQUE(line_id, name, wave_id)
);

CREATE TABLE IF NOT EXISTS item_images (
    id          TEXT PRIMARY KEY,
    item_id     TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    url         TEXT,
    local_path  TEXT,
    caption     TEXT,
    sort_order  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS collection_entries (
    id                  TEXT PRIMARY KEY,
    item_id             TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE UNIQUE,
    owned               INTEGER DEFAULT 0,
    wishlist_priority   INTEGER DEFAULT 0,
    quantity            INTEGER DEFAULT 1,
    condition           TEXT,
    box_condition       TEXT,
    packaging_state     TEXT,
    completeness        TEXT,
    is_complete         INTEGER DEFAULT 1,
    missing_accessories TEXT,
    acquired_date       TEXT,
    paid_price          REAL,
    acquired_from       TEXT,
    estimated_value     REAL,
    personal_rating     INTEGER,
    is_favorite         INTEGER DEFAULT 0,
    on_display          INTEGER DEFAULT 0,
    needs_repair        INTEGER DEFAULT 0,
    is_loaned           INTEGER DEFAULT 0,
    loaned_to           TEXT,
    is_for_sale         INTEGER DEFAULT 0,
    is_sealed           INTEGER DEFAULT 0,
    personal_notes      TEXT,
    created_at          TEXT,
    updated_at          TEXT
);

CREATE TABLE IF NOT EXISTS personal_photos (
    id          TEXT PRIMARY KEY,
    item_id     TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    local_path  TEXT NOT NULL,
    caption     TEXT,
    sort_order  INTEGER DEFAULT 0,
    added_at    TEXT
);

CREATE TABLE IF NOT EXISTS tags (
    id      TEXT PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE,
    color   TEXT
);

CREATE TABLE IF NOT EXISTS item_tags (
    item_id TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    tag_id  TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (item_id, tag_id)
);

CREATE TABLE IF NOT EXISTS variants (
    id              TEXT PRIMARY KEY,
    parent_item_id  TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    notes           TEXT,
    source_key      TEXT,
    primary_image   TEXT
);

CREATE TABLE IF NOT EXISTS import_log (
    id              TEXT PRIMARY KEY,
    source_id       TEXT NOT NULL,
    target_type     TEXT NOT NULL,
    target_id       TEXT,
    target_name     TEXT,
    imported_at     TEXT NOT NULL,
    items_added     INTEGER DEFAULT 0,
    items_updated   INTEGER DEFAULT 0,
    status          TEXT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS auction_log (
    id                  TEXT PRIMARY KEY,
    item_id             TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    listing_id          TEXT,
    listing_url         TEXT,
    seller              TEXT,
    final_price         REAL,
    currency            TEXT DEFAULT 'USD',
    condition_label     TEXT,
    condition_notes     TEXT,
    auction_end_date    TEXT,
    status              TEXT,
    notes               TEXT,
    logged_at           TEXT NOT NULL
);
"""


def apply_schema(conn: sqlite3.Connection) -> None:
    for statement in _TABLES.strip().split(";"):
        stmt = statement.strip()
        if stmt:
            conn.execute(stmt)
    conn.commit()
