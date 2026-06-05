# Figure Archive — Application Specification
### A local-first action figure collection tracker with external database import

**Version:** 1.0
**Target platform:** Windows (PySide6)
**Relationship to Scratchpad:** Standalone application. Shares code conventions, PySide6 patterns, and packaging approach with Scratchpad. A future bridge allows linking Figure Archive entries to Scratchpad Custom project nodes, but the two apps are independent and do not share a codebase directly.

---

## Table of Contents

1. [Overview & Philosophy](#1-overview--philosophy)
2. [Tech Stack](#2-tech-stack)
3. [Core Concepts & Terminology](#3-core-concepts--terminology)
4. [Data Model](#4-data-model)
5. [File & Folder Structure](#5-file--folder-structure)
6. [The Source Plugin System](#6-the-source-plugin-system)
7. [Built-in Source Plugins](#7-built-in-source-plugins)
8. [UI Layout & Navigation](#8-ui-layout--navigation)
9. [Collection Management Features](#9-collection-management-features)
10. [Import & Sync Workflow](#10-import--sync-workflow)
11. [Export & Sharing](#11-export--sharing)
12. [Implementation Priorities](#12-implementation-priorities)

---

## 1. Overview & Philosophy

Figure Archive is a **local-first, offline-capable desktop application** for tracking a personal action figure collection. The core workflow is:

1. Import a toyline (or individual figures) from an external database website via a source plugin
2. The full checklist for that line is stored locally — every figure, vehicle, and playset in the line is in your local database whether you own it or not
3. You mark which items you own, which you want, and which you've sold or passed on
4. You add your own photos, notes, tags, and condition ratings to your owned items
5. You browse, search, and filter your full collection across all lines

The app is **not** a web service. There are no accounts, no cloud sync, no subscription. Your collection data lives in a local SQLite database. Images are cached locally. The app works fully offline once data is imported.

### Key design principles

- **Checklist-first.** A toyline is an authoritative list of everything released. You check off what you own. This is the fundamental action collector UX.
- **Lines and sublines are first-class.** Transformers has Generation 1, Beast Wars, Armada, etc. Mighty Max has Doom Zones, Battle Warriors, etc. These are not tags — they are structural separators in the UI.
- **Source plugins are the data layer.** Every external database (figure-archive.net, figurerealm.com, transformerland.com, etc.) is a plugin. The app's core doesn't care where data comes from.
- **Manual entry is always available.** If no source plugin covers a line, the user can create a line and its figures by hand.
- **Your personal data is separate from imported data.** Ownership status, condition, notes, photos, tags, and favorites are stored in your personal collection layer and are never overwritten by a re-import or sync.

---

## 2. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | |
| UI framework | PySide6 | Qt6 bindings |
| Database | SQLite via `sqlite3` stdlib | Single `.db` file per collection |
| HTTP scraping | `requests` + `BeautifulSoup4` | For source plugins |
| Rate limiting | `time.sleep()` + per-plugin config | Respectful scraping |
| Image cache | Local folder, `Pillow` for thumbnails | Cached by URL hash |
| PDF export | WeasyPrint | |
| Plugin loading | Python `importlib` | `.py` files in `/plugins/sources/` |

### Dependencies (requirements.txt)
```
PySide6>=6.6.0
requests>=2.31.0
beautifulsoup4>=4.12.0
Pillow>=10.0.0
WeasyPrint>=60.0
lxml>=4.9.0
```

---

## 3. Core Concepts & Terminology

### Collection
The user's personal database — a single SQLite `.db` file. One collection per user (but the app supports opening different collection files, useful if you have separate collections for different genres or household members).

### Franchise
The top-level grouping. Examples: Transformers, G.I. Joe, Masters of the Universe, Mighty Max, Marvel Legends, Star Wars Black Series. A Franchise groups one or more Lines.

### Line
A named release within a Franchise. Examples under Transformers: Generation 1, Beast Wars, Armada, Cybertron, Prime, Generations. A Line groups one or more Waves (or is flat if the line has no wave structure).

### Wave / Series / Assortment
An optional sub-grouping within a Line. Examples: "Wave 1", "Series 3", "Doom Zones", "Battle Warriors". Some lines have no wave structure and items sit directly under the Line.

### Item
A single product — a figure, vehicle, playset, accessory pack, or gift set. An Item always belongs to a Wave (or directly to a Line if waveless). Items are the atomic unit of the checklist.

Items have two layers:
- **Catalog data** — name, description, year, manufacturer, images, accessories list, scale, UPC — imported from a source or entered manually. This is the authoritative reference data.
- **Personal data** — ownership status, condition, paid price, acquisition date, personal photos, notes, tags, favorite flag, custom rating. This is yours and is never overwritten by imports.

### Separator
A UI concept, not a data concept. Waves and sub-groupings within a Line are displayed as **separators** in the checklist view — visual dividers with the wave name. This matches how collectors mentally organize lines (Mighty Max Doom Zones vs. Battle Warriors are not sub-databases, they're just labeled separators in the Mighty Max checklist).

### Source Plugin
A Python module that knows how to scrape a specific external database and return standardized data objects. Source plugins are the only place where HTTP requests happen. See Section 6.

### Import
The process of running a source plugin to fetch catalog data for a Franchise, Line, or specific Item and store it locally. Imports are not live — the data is cached. A re-import updates catalog data but never touches personal data.

---

## 4. Data Model

The database is SQLite. All tables below.

### 4.1 Schema

```sql
-- Source plugins registered in this collection
CREATE TABLE sources (
    id          TEXT PRIMARY KEY,   -- plugin id e.g. "figure_archive"
    name        TEXT NOT NULL,
    last_used   TEXT                -- ISO datetime
);

-- Franchises
CREATE TABLE franchises (
    id          TEXT PRIMARY KEY,   -- UUID
    name        TEXT NOT NULL,
    source_id   TEXT,               -- which plugin this came from (null = manual)
    source_key  TEXT,               -- the source's internal ID/URL fragment for this franchise
    sort_order  INTEGER DEFAULT 0,
    notes       TEXT,
    banner_image TEXT               -- local path to cached banner image
);

-- Lines within a franchise
CREATE TABLE lines (
    id            TEXT PRIMARY KEY,
    franchise_id  TEXT NOT NULL REFERENCES franchises(id),
    name          TEXT NOT NULL,
    year_start    INTEGER,
    year_end      INTEGER,
    manufacturer  TEXT,
    source_id     TEXT,
    source_key    TEXT,
    sort_order    INTEGER DEFAULT 0,
    notes         TEXT,
    thumbnail     TEXT              -- local path
);

-- Waves/series within a line (optional; items may belong directly to a line)
CREATE TABLE waves (
    id          TEXT PRIMARY KEY,
    line_id     TEXT NOT NULL REFERENCES lines(id),
    name        TEXT NOT NULL,      -- "Wave 1", "Doom Zones", "Series 3", etc.
    year        INTEGER,
    sort_order  INTEGER DEFAULT 0,
    notes       TEXT
);

-- Items (figures, vehicles, playsets, etc.)
CREATE TABLE items (
    id              TEXT PRIMARY KEY,
    line_id         TEXT NOT NULL REFERENCES lines(id),
    wave_id         TEXT REFERENCES waves(id),  -- null = directly under line
    name            TEXT NOT NULL,
    item_type       TEXT NOT NULL DEFAULT 'figure',  -- figure, vehicle, playset, accessory, giftset, other
    year            INTEGER,
    manufacturer    TEXT,
    scale           TEXT,           -- "3.75-inch", "6-inch", "12-inch", etc.
    upc             TEXT,
    description     TEXT,
    accessories     TEXT,           -- comma-separated or JSON list of accessory names
    source_id       TEXT,
    source_key      TEXT,           -- source's URL or ID for this item
    source_url      TEXT,           -- full URL for reference
    sort_order      INTEGER DEFAULT 0,
    -- Catalog images (cached from source)
    primary_image   TEXT,           -- local cache path
    UNIQUE(line_id, name, wave_id)  -- prevent duplicate imports
);

-- Additional images per item (catalog images from source)
CREATE TABLE item_images (
    id          TEXT PRIMARY KEY,
    item_id     TEXT NOT NULL REFERENCES items(id),
    url         TEXT,               -- original source URL
    local_path  TEXT,               -- local cache path
    caption     TEXT,
    sort_order  INTEGER DEFAULT 0
);

-- ============================================================
-- PERSONAL COLLECTION DATA — never overwritten by imports
-- ============================================================

CREATE TABLE collection_entries (
    id              TEXT PRIMARY KEY,
    item_id         TEXT NOT NULL REFERENCES items(id) UNIQUE,
    -- Ownership
    owned           INTEGER DEFAULT 0,  -- 0=no, 1=yes, 2=sold/traded, 3=wanted
    quantity        INTEGER DEFAULT 1,
    -- Condition
    condition       TEXT,           -- Mint, Near Mint, Good, Fair, Poor, Loose, MISB, MOC
    completeness    TEXT,           -- Complete, Missing Accessories, Parts Only, etc.
    -- Acquisition
    acquired_date   TEXT,
    paid_price      REAL,
    acquired_from   TEXT,
    -- Current value (user-entered)
    estimated_value REAL,
    -- Personal rating
    personal_rating INTEGER,        -- 1-5
    -- Flags
    is_favorite     INTEGER DEFAULT 0,
    on_display      INTEGER DEFAULT 0,
    -- Notes
    personal_notes  TEXT,
    -- Timestamps
    created_at      TEXT,
    updated_at      TEXT
);

-- Personal photos for owned items (separate from catalog images)
CREATE TABLE personal_photos (
    id          TEXT PRIMARY KEY,
    item_id     TEXT NOT NULL REFERENCES items(id),
    local_path  TEXT NOT NULL,      -- always stored in /personal_photos/
    caption     TEXT,
    sort_order  INTEGER DEFAULT 0,
    added_at    TEXT
);

-- Tags (user-defined)
CREATE TABLE tags (
    id      TEXT PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE,
    color   TEXT                    -- hex color for tag chip display
);

CREATE TABLE item_tags (
    item_id TEXT NOT NULL REFERENCES items(id),
    tag_id  TEXT NOT NULL REFERENCES tags(id),
    PRIMARY KEY (item_id, tag_id)
);

-- Variants / reissues (linked to a parent item)
CREATE TABLE variants (
    id              TEXT PRIMARY KEY,
    parent_item_id  TEXT NOT NULL REFERENCES items(id),
    name            TEXT NOT NULL,  -- "Gold variant", "Toys R Us exclusive", "Reissue 2003"
    notes           TEXT,
    source_key      TEXT,
    primary_image   TEXT
);

-- Import log
CREATE TABLE import_log (
    id          TEXT PRIMARY KEY,
    source_id   TEXT NOT NULL,
    target_type TEXT NOT NULL,      -- "franchise", "line", "wave", "item"
    target_id   TEXT,               -- the ID that was imported
    target_name TEXT,
    imported_at TEXT NOT NULL,
    items_added INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    status      TEXT,               -- "success", "partial", "failed"
    notes       TEXT
);
```

### 4.2 Item Types

| Type | Examples |
|---|---|
| `figure` | Standard action figure |
| `vehicle` | Optimus Prime cab, Cobra HISS Tank |
| `playset` | Castle Grayskull, Doom Zones set |
| `accessory` | Weapon packs, armor sets, stands |
| `giftset` | Multi-figure boxed sets |
| `other` | Anything that doesn't fit above |

### 4.3 Ownership Statuses

| Value | Label | Description |
|---|---|---|
| `0` | Not owned | Default for all imported items |
| `1` | Owned | In your collection |
| `2` | Sold / Traded | Was owned, no longer |
| `3` | Wanted | On your wishlist |

---

## 5. File & Folder Structure

```
%APPDATA%\FigureArchive\
  config.json                   ← app settings, last opened collection path
  collections\
    my_collection\
      collection.db             ← SQLite database
      image_cache\              ← images downloaded from sources
        [url_hash].jpg          ← cached by MD5 hash of source URL
        [url_hash]_thumb.jpg    ← 256x256 thumbnail version
      personal_photos\
        [item_uuid]\
          photo_01.jpg
          photo_02.jpg
      exports\
        checklist_transformers_g1.pdf
        collection_summary.html
```

Multiple collections are supported by opening a different `collection.db` file via File > Open Collection.

### Image caching rules
- All catalog images fetched from sources are stored in `image_cache/` named by MD5 hash of the original URL
- A 256×256 thumbnail is generated for each and stored as `[hash]_thumb.jpg`
- Personal photos are stored in `personal_photos/[item_uuid]/` and are never deleted by re-imports
- If a cached image is missing and the app is online, it is re-fetched on demand
- Pillow handles all image operations

---

## 6. The Source Plugin System

### Overview

A source plugin is a Python file in `plugins/sources/`. It is responsible for:
1. Fetching a list of Franchises (or Lines within a Franchise) from its target site
2. Fetching all Items within a Line or Wave
3. Returning standardized Python objects that the app stores in SQLite

Plugins do **not** write to the database directly. They return data objects. The import engine handles DB writes, deduplication, and logging.

### Plugin interface

Every source plugin must implement this interface:

```python
# plugins/sources/base.py

class SourcePlugin:
    """Base class for all source plugins."""

    # Required class attributes
    id: str                     # unique snake_case id, e.g. "figure_archive"
    name: str                   # display name, e.g. "The Action Figure Archive"
    base_url: str               # e.g. "http://figure-archive.net"
    description: str
    supports_browse: bool       # can browse full franchise/line tree?
    supports_search: bool       # can search by name?
    rate_limit_seconds: float   # minimum seconds between requests (be respectful)

    def get_franchises(self) -> list[FranchiseData]:
        """Return a list of all franchises/toylines available from this source."""
        raise NotImplementedError

    def get_lines(self, franchise: FranchiseData) -> list[LineData]:
        """Return all lines within a franchise."""
        raise NotImplementedError

    def get_waves(self, line: LineData) -> list[WaveData]:
        """Return all waves within a line. Return [] if line has no wave structure."""
        raise NotImplementedError

    def get_items(self, line: LineData, wave: WaveData | None = None) -> list[ItemData]:
        """Return all items in a wave (or full line if wave is None)."""
        raise NotImplementedError

    def get_item_detail(self, item: ItemData) -> ItemData:
        """Fetch full detail for a single item (description, accessories, all images)."""
        raise NotImplementedError

    def search(self, query: str) -> list[ItemData]:
        """Search by name. Only implement if supports_search = True."""
        raise NotImplementedError
```

### Data transfer objects

```python
# plugins/sources/base.py (continued)

from dataclasses import dataclass, field

@dataclass
class FranchiseData:
    source_key: str             # source's internal ID or URL fragment
    name: str
    manufacturer: str = ""
    source_url: str = ""
    banner_image_url: str = ""
    notes: str = ""

@dataclass
class LineData:
    source_key: str
    franchise_source_key: str
    name: str
    year_start: int = 0
    year_end: int = 0
    manufacturer: str = ""
    source_url: str = ""
    thumbnail_url: str = ""
    notes: str = ""

@dataclass
class WaveData:
    source_key: str
    line_source_key: str
    name: str
    year: int = 0
    sort_order: int = 0
    notes: str = ""

@dataclass
class ItemData:
    source_key: str
    line_source_key: str
    wave_source_key: str = ""
    name: str = ""
    item_type: str = "figure"   # figure, vehicle, playset, accessory, giftset, other
    year: int = 0
    manufacturer: str = ""
    scale: str = ""
    upc: str = ""
    description: str = ""
    accessories: list[str] = field(default_factory=list)
    primary_image_url: str = ""
    additional_image_urls: list[str] = field(default_factory=list)
    source_url: str = ""
    variants: list[str] = field(default_factory=list)  # variant names
    sort_order: int = 0
```

### Import engine (core, not a plugin)

The import engine (`scratchpad.importer`) handles:
- Calling the plugin methods
- Rate limiting (respects `plugin.rate_limit_seconds`)
- Downloading and caching images
- Writing to SQLite with deduplication (match on `source_key` and `line_id`)
- **Never overwriting** any field in `collection_entries` or `personal_photos`
- Logging to `import_log`
- Progress reporting (emits Qt signals for the progress dialog)

---

## 7. Built-in Source Plugins

### 7.1 figure-archive.net

**ID:** `figure_archive`
**Base URL:** `http://figure-archive.net`
**Rate limit:** 2.0 seconds between requests
**Supports browse:** Yes
**Supports search:** Yes (via their search functionality)

**Data available:**
- Manufacturer index → Toyline index → Assortment list → Figure checklist
- Figure entries include: name, year, image (when available), accessories
- Over 50,000 items and 62,000 images

**Scraping approach:**
- Parse the left-frame index (`indexL.aspx`) for manufacturer and line navigation
- Each line links to a checklist page listing all items in that line
- Item pages contain name, image, and accessory data

---

### 7.2 Figure Realm

**ID:** `figure_realm`
**Base URL:** `https://www.figurerealm.com`
**Rate limit:** 2.0 seconds between requests
**Supports browse:** Yes
**Supports search:** Yes

**Data available:**
- Series browser (`/actionfigure`) lists all series with thumbnail grids
- Each series page lists all figures with images
- Individual figure pages include accessories, description, variants

**Scraping approach:**
- Browse series list, paginating through results
- Each series page lists figures as thumbnails; parse name and image URL
- Follow individual figure links for detail (accessories, description)

---

### 7.3 Transformerland Wiki

**ID:** `transformerland`
**Base URL:** `https://www.transformerland.com/wiki/`
**Rate limit:** 2.0 seconds between requests
**Supports browse:** Yes
**Supports search:** No (use figure_realm for TF search instead)
**Franchise scope:** Transformers only

**Data available:**
- Detailed wiki pages for individual Transformers figures
- Generation 1, Beast Wars, and other lines covered
- Tech spec ratings, accessories, bio text

**Scraping approach:**
- Navigate series category pages to enumerate figures
- Parse individual figure wiki pages for name, image, tech specs, accessories

---

### 7.4 The Action Figure Database (theafdb.com)

**ID:** `theafdb`
**Base URL:** `https://theafdb.com`
**Rate limit:** 2.5 seconds between requests
**Supports browse:** Yes
**Supports search:** Yes

**Data available:**
- Brand → Toyline → Figure hierarchy
- Collection tracking (AFDB has its own tracker, but we import catalog data only)
- Figure name, image, year, manufacturer

---

### 7.5 Manual Entry (built-in, always available)

**ID:** `manual`
**No HTTP requests.** The user creates a Franchise, Lines, Waves, and Items by hand using the UI.

This is not a plugin in the technical sense — it's the fallback for lines not covered by any source plugin. All manually entered items have `source_id = "manual"` and no `source_key` or `source_url`.

---

### 7.6 Plugin development guidelines

To add a new source plugin, create `/plugins/sources/my_source.py` that:
1. Imports and subclasses `SourcePlugin` from `plugins.sources.base`
2. Sets all required class attributes
3. Implements all required methods (raise `NotImplementedError` for optional ones)
4. Sets `PLUGIN = MySourcePlugin` at module level (the loader looks for this)

The plugin is discovered automatically at app startup. No registration step needed.

**Be respectful:** All plugins must respect `rate_limit_seconds`. The import engine enforces this but plugins should also document expected crawl times (e.g. "Importing a full 200-item line takes approximately 7 minutes at 2s rate limit").

---

## 8. UI Layout & Navigation

### 8.1 Home Screen / Library View

```
+----------------------------------------------------------+
|  [🗄] Figure Archive            [Settings] [Open DB]     |
+----------------------------------------------------------+
|  My Collection                                           |
|  3,241 items  |  847 owned  |  124 wanted  |  12 lines  |
|                                                          |
|  Quick stats:   ████████░░  68% of Transformers G1      |
|                 ██░░░░░░░░  18% of Mighty Max           |
|                 ████░░░░░░  42% of MOTU Classics        |
|                                                          |
|  Recent activity:                                        |
|  > Marked "Optimus Prime (G1)" as owned  — 2 days ago   |
|  > Imported Mighty Max Battle Warriors  — 1 week ago    |
|                                                          |
|  [Browse Collection]  [Import New Line]  [Search All]   |
+----------------------------------------------------------+
```

### 8.2 Main Window Layout

```
+------------------+--------------------------------------------+
|  FRANCHISES      |  Line / Checklist view                     |
|                  |                                            |
|  ▼ Transformers  |  Transformers — Generation 1               |
|    Generation 1  |  ──────────────────────────────────────    |
|    Beast Wars    |  Autobot Cars (Wave 1, 1984)               |
|    Armada        |  ──────────────────────────────────────    |
|    Prime         |  ☑ Optimus Prime       [★] [owned] [♥]   |
|                  |  ☑ Bumblebee           [★] [owned]        |
|  ▼ Mighty Max    |  ☐ Ironhide                                |
|    Doom Zones    |  ☐ Ratchet                                 |
|    Battle Warr.  |  ☐ Sideswipe                              |
|    Skull Masters |  ☐ Sunstreaker                            |
|                  |  ──────────────────────────────────────    |
|  ▼ G.I. Joe      |  Decepticons (Wave 1, 1984)               |
|    ARAH          |  ──────────────────────────────────────    |
|    …             |  ☐ Megatron                               |
|                  |  ☐ Starscream                             |
|  [+ Add Line]    |  ☐ Soundwave                              |
|  [Import Line]   |  ☑ Ravage               [owned]           |
+------------------+--------------------------------------------+
|  [Filter: All ▾] [Search: ___________] [View: List/Grid ▾]   |
+----------------------------------------------------------+----+
```

### 8.3 Sidebar — Franchise/Line Tree

- Franchises are collapsible top-level items
- Lines are children of franchises
- Waves do **not** appear in the sidebar tree — they appear as **separators** (visual dividers with bold label) inside the checklist view
- Right-clicking a Line: Import/Refresh, Edit, Delete, Export Checklist
- Right-clicking a Franchise: Add Line, Edit, Delete
- Drag-and-drop to reorder lines within a franchise

### 8.4 Checklist View (List Mode)

The default view. One row per item.

Each row shows:
- Checkbox (owned toggle — click to mark owned/not owned)
- Primary thumbnail (small, ~48px)
- Item name
- Year (if known)
- Item type badge (figure / vehicle / playset / etc.)
- Ownership status badge (Owned / Wanted / Sold)
- Favorite star (click to toggle)
- Personal rating (1–5 stars, shown if rated)
- Condition (shown if owned)

Rows are separated by **wave separators** — full-width rows with the wave name in bold, item count, and owned/total stats (e.g. "Wave 1, 1984 — 6 items — 3 owned").

Clicking a row opens the Item Detail panel on the right (or in a split view).

### 8.5 Grid View

An alternative visual view — larger cards with the primary image prominent, item name below, and a small ownership badge overlay. Good for visually browsing a line. Toggle between list and grid via the View button.

Grid card size: Small (4+ columns), Medium (3 columns), Large (2 columns) — user preference.

### 8.6 Item Detail Panel

Opens when an item is selected. Splits the right side of the window.

```
+------------------------------------------------+
|  [←] Bumblebee                       [♥] [★] |
|  Transformers > Generation 1 > Autobot Cars    |
|                                                |
|  [image carousel — catalog images]             |
|                                                |
|  Year: 1984    Scale: 3.75"    Type: Figure    |
|  Manufacturer: Hasbro                          |
|  UPC: 653569123456                             |
|                                                |
|  Accessories: Rocket launcher, missile,        |
|  left & right door shields                     |
|                                                |
|  Description: (source text)                    |
|                                                |
|  ──── Your Collection ────                     |
|  Status: [Owned ▾]  Qty: [1]                   |
|  Condition: [Near Mint ▾]                      |
|  Completeness: [Complete ▾]                    |
|  Acquired: [date picker]  From: [__________]   |
|  Paid: [$_____]  Est. Value: [$_____]          |
|  Rating: [★★★★☆]                              |
|                                                |
|  Tags: [vintage] [childhood] [+ add tag]       |
|                                                |
|  Personal photos:                              |
|  [+] [photo 1] [photo 2]                       |
|                                                |
|  Notes:                                        |
|  [_________________________________]           |
|  [_________________________________]           |
|                                                |
|  [Save]            [View on Source Site ↗]    |
+------------------------------------------------+
```

All personal data auto-saves after a 1.5-second debounce (same pattern as Scratchpad).

### 8.7 Search

A global search bar in the toolbar. Searches across:
- Item names (all lines)
- Line names
- Franchise names
- Notes (personal notes field)
- Tags

Results show franchise > line context for each item. Clicking a result navigates to that item in its checklist and opens the detail panel.

Filter options in the search/filter bar:
- Ownership: All / Owned / Not Owned / Wanted / Sold
- Type: All / Figure / Vehicle / Playset / Accessory / Gift Set
- Condition: (any condition value)
- Favorites only
- On display only
- Year range
- Tag filter (multi-select)
- Rating (minimum stars)

---

## 9. Collection Management Features

### 9.1 Batch operations

Right-click multiple selected items (or use Edit > Select All in current view):
- Mark all as Owned
- Mark all as Wanted
- Add tag to all
- Set condition for all
- Remove all from collection

### 9.2 Quick-mark mode

A toolbar toggle "Quick-mark mode" — while active, clicking anywhere on a row (not just the checkbox) toggles owned status. Useful for rapidly checking off a newly imported line.

### 9.3 Favorites

Any item can be starred as a favorite. A Favorites view in the sidebar shows all favorited items across all lines.

### 9.4 Tags

User-defined tags with optional color. Tags are global (shared across all lines). Examples: "childhood", "vintage", "custom target", "on display", "grail", "variant hunt."

A tag management screen (Settings > Tags) lets you create, rename, recolor, and delete tags. Deleting a tag removes it from all items.

### 9.5 Custom sorting

Within a Line, the default sort is by wave then by `sort_order` (the order items appear in the source checklist). The user can also sort by:
- Name (A–Z / Z–A)
- Year
- Personal rating
- Acquisition date
- Paid price

### 9.6 Collection statistics

A Statistics screen (accessible from the home screen or View menu):

- Total items in library, total owned, total wanted
- Breakdown by franchise (items / owned / wanted / completion %)
- Breakdown by item type (how many figures vs. vehicles vs. playsets owned)
- Total paid (sum of all `paid_price` entries)
- Total estimated value (sum of all `estimated_value` entries)
- Completion bars per line (visual progress bar)

### 9.7 Display shelf mode

A "Display" toggle per item (`on_display` flag). A "On Display" view shows only display-flagged items — useful for tracking what's currently on your shelf vs. in storage.

---

## 10. Import & Sync Workflow

### 10.1 Import dialog

Triggered by "Import New Line" button or toolbar item.

```
+--------------------------------------------------+
|  Import from Source                              |
|                                                  |
|  Source:  [Figure Archive ▾]                     |
|                                                  |
|  Browse:                                         |
|  ▼ Hasbro                                        |
|    ▼ Transformers                                |
|      Generation 1          [Import]              |
|      Beast Wars            [Import]              |
|      Armada                [Import]              |
|    ▼ G.I. Joe                                    |
|      A Real American Hero  [Import]              |
|  ▼ Mattel                                        |
|    ▼ Masters of the Universe                     |
|      Original (1982)       [Import]              |
|      …                                           |
|                                                  |
|  Or search:  [________________________] [Search] |
|                                                  |
|  [Cancel]                                        |
+--------------------------------------------------+
```

Clicking Import on a Line opens a progress dialog:
- Shows items found, items imported, images downloaded
- Can be cancelled (partial imports are kept)
- On completion: "Imported 187 items for Transformers Generation 1. 0 items already in collection marked owned."

### 10.2 Re-import / refresh

Right-click any Line > Refresh from Source.

The import engine:
1. Re-fetches all items from the source
2. For items already in the DB (matched on `source_key`): updates catalog fields (name, description, accessories, images) — **never touches personal data**
3. For new items (not in DB): adds them with ownership = 0
4. Does NOT delete items that were in the DB but are missing from the source (they are flagged with `source_key = "orphaned"` and shown with a small "not found in source" indicator)
5. Logs everything to `import_log`

### 10.3 Import from URL

For source plugins that support it, the user can paste a direct URL (e.g. a specific series page on figurerealm.com) and the plugin will attempt to detect and import that page directly.

### 10.4 Import from CSV / manual bulk entry

File > Import from CSV opens a mapping dialog. The user selects a CSV file and maps columns to fields (name, year, wave, type, etc.). Useful for importing from a spreadsheet the user already maintains.

CSV import creates items with `source_id = "csv_import"`.

---

## 11. Export & Sharing

### 11.1 Export checklist (PDF)

Right-click a Line > Export Checklist as PDF.

Generates a formatted PDF checklist showing all items in the line, with a checkbox column, item name, year, and optional thumbnail column. Useful for printing and taking to toy shows or conventions.

Options:
- Include thumbnails (yes/no)
- Show only unowned items (shopping list mode)
- Show owned status column
- Page size (A4 / US Letter)

### 11.2 Export collection summary (PDF/HTML)

View > Export Collection Summary. Generates a full collection report:
- Cover page with stats
- One section per franchise, showing all lines and completion bars
- List of all owned items with condition and value
- Total paid and estimated value

### 11.3 Export to CSV

File > Export to CSV. Exports the full collection (or current filtered view) as a CSV with all fields. Useful for spreadsheet use or backup.

### 11.4 Collection backup

File > Backup Collection. Copies the `.db` file and `personal_photos/` folder to a user-selected location as a timestamped zip. The `image_cache/` is not backed up (it can be re-downloaded).

---

## 12. Implementation Priorities

### Phase 1 — Core shell and data layer
- [ ] App window, home screen layout
- [ ] SQLite database creation with full schema
- [ ] Create Franchise and Line manually
- [ ] Sidebar tree rendering (franchises and lines)
- [ ] Checklist view with wave separators
- [ ] Ownership checkbox toggle (owned / not owned)
- [ ] Item Detail panel — personal data fields, auto-save
- [ ] Image display (placeholder if no image)

### Phase 2 — Source plugin system
- [ ] Plugin base class and data transfer objects
- [ ] Plugin loader (`importlib` scan of `/plugins/sources/`)
- [ ] Import engine (rate-limited fetching, DB write, deduplication, image cache)
- [ ] Import progress dialog with cancel support
- [ ] Import log viewer
- [ ] Figure Archive plugin (`figure_archive`)

### Phase 3 — Additional source plugins
- [ ] Figure Realm plugin (`figure_realm`)
- [ ] Transformerland Wiki plugin (`transformerland`)
- [ ] The Action Figure Database plugin (`theafdb`)
- [ ] Import from URL (paste a direct series page URL)

### Phase 4 — Collection features
- [ ] Tags system (create, assign, filter, manage)
- [ ] Favorites toggle and Favorites view
- [ ] Quick-mark mode
- [ ] Batch operations on multi-selected items
- [ ] Personal photos (drag-drop, add, remove, reorder)
- [ ] Grid view
- [ ] Full search with filters
- [ ] Display shelf mode

### Phase 5 — Statistics and export
- [ ] Collection statistics screen
- [ ] Export checklist as PDF (WeasyPrint)
- [ ] Export collection summary as PDF/HTML
- [ ] Export to CSV
- [ ] Import from CSV
- [ ] Collection backup (zip)

### Phase 6 — Polish
- [ ] Re-import / refresh from source with orphan detection
- [ ] Variants support in item detail
- [ ] Custom sort order within lines
- [ ] Settings screen (image cache management, tag management, source plugin settings)
- [ ] Recent activity feed on home screen
- [ ] Completion progress bars per line on home screen

---

*End of spec. Version 1.0*
