# FigureArchive — Build Steps

Each phase ends with a concrete, runnable, testable product.
Tasks are written as small discrete units of work.

Reference documents:
- `SPEC.md` — full application specification
- `RESEARCH_AND_DESIGN_NOTES.md` — architecture decisions and data source findings

---

## Phase 1 — Running Window with a Database

**Deliverable:** On first launch a welcome dialog asks the user to name and locate
their collection. After that the main window opens, and you can create a Franchise,
add a Line to it, and see both in a sidebar tree. Nothing imports, nothing scrapes.
Pure manual entry and persistence.

**First-run decision:** Show a "Create your first collection" welcome dialog on
first launch (no silent auto-creation). This gives the user control over the
collection name and folder from day one and avoids having to retrofit it later.
Subsequent launches open the last-used collection directly (path stored in
`config.json`). File > New Collection and File > Open Collection are available at
any time to create or switch collections.

---

### 1.1 Folder structure

- [ ] Create the top-level layout:
  ```
  figure_archive/          ← Python package (the app)
    __init__.py
    __main__.py
    app.py
    core/
      __init__.py
      config.py
    db/
      __init__.py
      connection.py
      schema.py
      franchises.py
      lines.py
    ui/
      __init__.py
      main_window.py
      sidebar.py
      dialogs/
        __init__.py
        welcome_dialog.py
        franchise_dialog.py
        line_dialog.py
    plugins/
      __init__.py
      types/
        __init__.py
      sources/
        __init__.py
        base.py
    assets/
      styles/
        dark.qss
  requirements.txt
  ```
- [ ] Add an empty `__init__.py` to every subdirectory listed above

### 1.2 requirements.txt

- [ ] Add dependencies:
  ```
  PySide6>=6.6.0
  requests>=2.31.0
  beautifulsoup4>=4.12.0
  Pillow>=10.0.0
  WeasyPrint>=60.0
  lxml>=4.9.0
  ```

### 1.3 core/config.py — app-level settings

- [ ] Resolve the platform data directory:
  - Windows: `%APPDATA%\FigureArchive\`
  - Linux/Mac: `~/.local/share/FigureArchive/`
- [ ] Create that directory if it doesn't exist
- [ ] Load `config.json` from it on startup (empty dict if file doesn't exist)
- [ ] Save `config.json` on any change
- [ ] Expose: `get(key, default)`, `set(key, value)`, `app_data_dir()`,
  `collections_dir()` (returns `<app_data_dir>/collections/`)
- [ ] Key stored in config: `last_collection_path` (full path to last-opened `.db`)

### 1.4 db/connection.py — database connection

- [ ] `open_collection(db_path)` — opens the SQLite file at `db_path` with
  `sqlite3.connect()`; enables WAL mode and foreign keys; stores connection in a
  module-level variable; returns the connection
- [ ] `get_connection()` — returns the current open connection; raises if none open
- [ ] `close_collection()` — closes the current connection and clears the variable
- [ ] The connection is opened once at startup and reused everywhere

### 1.5 db/schema.py — full database schema

- [ ] Write all `CREATE TABLE IF NOT EXISTS` statements for every table:
  - From spec: `sources`, `franchises`, `lines`, `waves`, `items`, `item_images`,
    `collection_entries`, `personal_photos`, `tags`, `item_tags`, `variants`,
    `import_log`
  - From design notes: `auction_log`
- [ ] Add columns not in the original spec but decided in design notes:
  - `lines.type_plugin_id TEXT` — which collection type plugin this line uses
  - `collection_entries.wishlist_priority INTEGER DEFAULT 0` — 0/1/2 (Watching/Wanted/Grail)
  - `collection_entries.needs_repair INTEGER DEFAULT 0`
  - `collection_entries.is_loaned INTEGER DEFAULT 0`
  - `collection_entries.loaned_to TEXT`
  - `collection_entries.is_for_sale INTEGER DEFAULT 0`
  - `collection_entries.is_sealed INTEGER DEFAULT 0`
  - `collection_entries.packaging_state TEXT` — MOC/MIB/MISB/Loose/etc.
  - `collection_entries.box_condition TEXT` — separate from figure condition
  - `collection_entries.is_complete INTEGER DEFAULT 1`
  - `collection_entries.missing_accessories TEXT`
- [ ] `apply_schema(connection)` — runs all CREATE TABLE statements against a
  given connection; called once after opening any collection

### 1.6 ui/dialogs/welcome_dialog.py — first-run dialog

- [ ] `WelcomeDialog(QDialog)` — shown when `config.last_collection_path` is
  absent or points to a file that no longer exists
- [ ] Content:
  - App name / logo placeholder at top
  - "Create a new collection" section:
    - Collection name field (default: "My Collection")
    - Folder path field + Browse button (defaults to
      `<collections_dir>/<name>/`)
    - Collection name field auto-updates the folder path as the user types
  - "Open existing collection" section:
    - Browse button → file picker for `.db` files
  - OK button (disabled until a valid name is entered or an existing file is
    picked)
- [ ] On accept: either create the folder + open a new DB, or open the existing
  one; return the resolved DB path to the caller
- [ ] On reject (close without completing): quit the application

### 1.7 app.py + __main__.py — entry point

- [ ] `__main__.py` — calls `main()` from `app.py`
- [ ] `app.py` `main()` function:
  1. Create `QApplication`
  2. Load and apply `dark.qss` stylesheet
  3. Load config
  4. If no valid `last_collection_path` in config, show `WelcomeDialog`
  5. Open the collection: `open_collection(path)` → `apply_schema(conn)`
  6. Save the path to config
  7. Create and show `MainWindow`
  8. Enter the Qt event loop

### 1.8 assets/styles/dark.qss — dark theme

- [ ] Set base colors for `QMainWindow`, `QWidget`, `QDialog`:
  - Background: `#1e1e2e` (dark navy)
  - Text: `#cdd6f4` (light lavender-white)
- [ ] Style `QSplitter::handle` — subtle divider line
- [ ] Style `QMenuBar` and `QMenu` — matching dark background
- [ ] Style `QTreeWidget` — dark background, highlight color on selected row
- [ ] Style `QPushButton` — rounded, accent color (`#89b4fa` blue) on hover
- [ ] Style `QLineEdit` and `QComboBox` — dark input fields, visible border
- [ ] Style `QDialog` — same background as main window
- [ ] Style `QLabel` — correct text color inheritance

### 1.9 ui/main_window.py — main window shell

- [ ] `MainWindow(QMainWindow)`:
  - Window title: "FigureArchive"
  - Minimum size: 900×600
  - A `QSplitter` (horizontal) as the central widget
  - Left pane: `Sidebar` widget (from `ui/sidebar.py`), fixed initial width 240px
  - Right pane: a `QStackedWidget` for swapping content (placeholder `QLabel`
    "Select a line to begin" for now)
  - Menu bar:
    - File > New Collection (opens WelcomeDialog in "create" mode)
    - File > Open Collection (file picker for `.db` files)
    - File > Quit
  - Status bar: shows current collection name and path

### 1.10 ui/sidebar.py — sidebar with franchise/line tree

- [ ] `Sidebar(QWidget)`:
  - A `QTreeWidget` filling the sidebar
  - A "New Franchise" button at the bottom
  - `load_tree()` — queries `franchises` and `lines` tables, populates the tree:
    franchises as top-level `QTreeWidgetItem`, lines as children
  - `refresh()` — clears and reloads the tree
  - Clicking a line item emits a `line_selected(line_id)` signal to the main window

### 1.11 db/franchises.py

- [ ] `create_franchise(name) -> str` — inserts row, returns new UUID
- [ ] `list_franchises() -> list[dict]` — returns all rows as dicts
- [ ] `rename_franchise(id, name)` — updates name
- [ ] `delete_franchise(id)` — deletes franchise and its child lines (cascade)

### 1.12 ui/dialogs/franchise_dialog.py

- [ ] `FranchiseDialog(QDialog)` — simple dialog with a name `QLineEdit`,
  OK (disabled until name is non-empty) and Cancel buttons
- [ ] Used for both create (empty field) and rename (pre-filled)

### 1.13 Wire franchise CRUD into sidebar

- [ ] "New Franchise" button → opens `FranchiseDialog` → on accept calls
  `create_franchise()` → calls `sidebar.refresh()`
- [ ] Right-click franchise node → context menu:
  - "Add Line" (opens line dialog, see below)
  - "Rename" → opens `FranchiseDialog` pre-filled → calls `rename_franchise()`
  - "Delete" → confirmation `QMessageBox` → calls `delete_franchise()` → refresh

### 1.14 db/lines.py

- [ ] `create_line(franchise_id, name, type_plugin_id="generic") -> str`
- [ ] `list_lines(franchise_id) -> list[dict]`
- [ ] `rename_line(id, name)`
- [ ] `delete_line(id)`

### 1.15 ui/dialogs/line_dialog.py

- [ ] `LineDialog(QDialog)` — fields: name `QLineEdit`, collection type
  `QComboBox` (hard-coded to just "Generic" for Phase 1; will be populated from
  plugins in Phase 4), OK/Cancel
- [ ] Used for both create and rename (type dropdown hidden on rename)

### 1.16 Wire line CRUD into sidebar

- [ ] Right-click franchise → "Add Line" → opens `LineDialog` → calls
  `create_line()` → refresh tree, expand parent franchise node
- [ ] Right-click line node → context menu:
  - "Rename" → opens `LineDialog` (name only) pre-filled
  - "Delete" → confirmation → calls `delete_line()` → refresh

**Phase 1 test:** Run `python -m figure_archive`.
- First launch: welcome dialog appears. Enter "My Transformers Collection",
  accept the default folder, click OK.
- Main window opens with dark theme, empty sidebar tree.
- Click "New Franchise" → enter "Transformers" → tree shows it.
- Right-click "Transformers" → "Add Line" → enter "Generation 1", type Generic →
  tree shows it as a child.
- Right-click "Transformers" → "Rename" → change to "Transformers (Hasbro)" →
  tree updates.
- Quit. Relaunch — welcome dialog is skipped, main window opens directly,
  "Transformers (Hasbro)" and "Generation 1" are still in the tree.

---

## Phase 2 — Items and the Checklist View

**Deliverable:** Select a Line in the sidebar and see an empty checklist.
Manually add items to the line. Each item appears as a row. Click a checkbox
to mark an item as owned. Data persists across restarts.

---

### 2.1 Item CRUD

- [ ] Write `db/items.py` — functions: `create_item(line_id, name, item_type)`,
  `list_items(line_id)`, `update_item(id, **fields)`, `delete_item(id)`
- [ ] Write `db/collection_entries.py` — functions:
  `get_or_create_entry(item_id)`, `set_owned(item_id, status)`,
  `update_entry(item_id, **fields)`

### 2.2 Checklist view widget

- [ ] Write `ui/checklist_view.py` — a `QWidget` containing a `QListWidget`
  (or custom `QAbstractItemModel` + `QListView`)
- [ ] Each row shows: checkbox, item name, year, type badge
- [ ] Clicking the checkbox calls `set_owned()` and updates the row visually
- [ ] Show a "Add Item" button above the list

### 2.3 Wire sidebar → checklist

- [ ] Clicking a Line in the sidebar loads that line's items into the checklist
  view in the right panel
- [ ] Show the franchise > line name as a header above the checklist

### 2.4 Wave separators

- [ ] Write `db/waves.py` — `create_wave(line_id, name)`, `list_waves(line_id)`
- [ ] When displaying items, group them by wave; render wave name as a
  non-interactive separator row (bold, full-width, different background color)
- [ ] Items with no wave appear at the top under an implicit "No Wave" group
  (or directly, if the line has no waves at all)

### 2.5 Add Item dialog

- [ ] Dialog fields: Name (required), Type (figure/vehicle/playset/etc. dropdown),
  Year (optional), Wave (dropdown of existing waves, or "No Wave")
- [ ] "New Wave" option in the wave dropdown opens a sub-dialog to create one

### 2.6 Ownership status badges

- [ ] Style the checklist rows:
  - Owned = green left border or badge
  - Wanted = blue
  - Not owned = no badge
- [ ] Add a status dropdown per row (or right-click menu): Owned / Wanted /
  Sold / Not Owned

**Phase 2 test:** Select Generation 1. Add three items: Optimus Prime (figure,
wave "Autobot Cars"), Bumblebee (figure, wave "Autobot Cars"), Megatron (figure,
wave "Decepticons"). See them grouped by wave with separators. Check Optimus as
owned. Quit and relaunch — Optimus is still checked.

---

## Phase 3 — Item Detail Panel

**Deliverable:** Click any item in the checklist and a detail panel opens on the
right side of the window. You can edit personal data (condition, notes, tags,
paid price, rating). All edits auto-save. A placeholder image area is shown.

---

### 3.1 Three-pane layout

- [ ] Split the right side of the main window into: checklist (left) and detail
  panel (right) using a `QSplitter`
- [ ] Detail panel is hidden when no item is selected; appears when one is clicked
- [ ] Detail panel has a close button (collapses it back)

### 3.2 Detail panel — catalog section

- [ ] Show at top: item name, franchise > line > wave breadcrumb
- [ ] Show catalog fields: Year, Type, Manufacturer, Scale, UPC, Description,
  Accessories (read-only for now — will be filled by imports later)
- [ ] A placeholder image box (grey rectangle with "No Image" text)

### 3.3 Detail panel — personal data section

- [ ] Status dropdown (Owned / Wanted / Sold / Not Owned / On Order)
- [ ] Wishlist priority dropdown (visible only when status is Wanted or On Order):
  Watching / Wanted / Grail
- [ ] Condition dropdowns: Figure Condition + Box/Package Condition (C-10 through
  C-1, plus Mint/NM/VG/Good/Poor simplified option)
- [ ] Packaging state dropdown: MOC / MIB / MISB / Loose / Incomplete / Parts Only
- [ ] `is_complete` checkbox + `missing_accessories` text field
- [ ] Boolean flags as checkboxes: Favorite, On Display, Needs Repair, Is Sealed,
  Is Loaned (+ Loaned To text field, shown only when checked)
- [ ] Acquired Date (date picker), Acquired From (text), Paid Price (number field)
- [ ] Estimated Value (number field)
- [ ] Personal Rating (1–5 star widget — five clickable stars)
- [ ] Personal Notes (multi-line text area)

### 3.4 Auto-save

- [ ] Connect all personal data fields to a single `_on_field_changed()` slot
- [ ] Start a 1.5-second `QTimer` on any change; reset it if another change comes
  in before it fires
- [ ] On timer fire, write all personal data fields to `collection_entries` via
  `update_entry()`
- [ ] Show a subtle "Saved" indicator for 2 seconds after each save

### 3.5 Tags

- [ ] Write `db/tags.py` — `create_tag(name, color)`, `list_tags()`,
  `add_tag_to_item(item_id, tag_id)`, `remove_tag_from_item(item_id, tag_id)`,
  `list_tags_for_item(item_id)`
- [ ] Tag display in detail panel: show existing tags as colored chips
- [ ] "+ Add Tag" button opens a dropdown of existing tags or a "New Tag" option
- [ ] New Tag dialog: name field + color picker

**Phase 3 test:** Click Optimus Prime. See the detail panel open. Set condition
to C-9, package to MOC, add a note "childhood grail", rate 5 stars, tag as
"childhood". Click Bumblebee — panel switches. Click back to Optimus — all
saved data is still there.

---

## Phase 4 — Plugin System Foundation

**Deliverable:** The plugin loader runs at startup and registers available
plugins. A "collection type" plugin for Action Figures is loaded and its field
definitions are used when creating a new Line. A manual-entry source plugin
is the only source, but the interface is established.

---

### 4.1 Plugin base classes

- [ ] Write `plugins/types/base.py` — `CollectionTypePlugin` base class with:
  `id`, `name`, `condition_vocabulary`, `packaging_states`,
  `has_accessory_list`, `item_fields` (list of `FieldDefinition` dataclasses),
  `compatible_source_ids`
- [ ] Write `plugins/sources/base.py` — `SourcePlugin` base class (from spec
  Section 6) plus `supports_url_import`, `supports_upc_lookup`,
  `supports_price_lookup`, `compatible_type_ids`
- [ ] Write `FieldDefinition` dataclass: `id`, `label`, `field_type`
  (text/integer/float/boolean/dropdown/date), `options` (for dropdowns),
  `required`, `default`

### 4.2 Plugin loader

- [ ] Write `plugins/loader.py` — scans `plugins/types/` and `plugins/sources/`
  for `.py` files, imports each, looks for `PLUGIN = SomeClass` at module level,
  instantiates and registers them in two dicts: `TYPE_PLUGINS` and
  `SOURCE_PLUGINS`
- [ ] Call loader at app startup; log which plugins were found

### 4.3 Action Figures type plugin

- [ ] Write `plugins/types/action_figures.py` — `ActionFiguresTypePlugin` with:
  - Condition vocabulary: C-10, C-9.5, C-9, C-8, C-7, C-6, C-5, C-4, C-3, C-2,
    C-1 (and simplified: Mint, Near Mint, Very Good, Good, Poor)
  - Packaging states: MOC, MIB, MISB, Loose, Complete, Incomplete, Parts Only
  - `has_accessory_list = True`
  - Extra item fields: Scale, UPC, Accessories (text list)
- [ ] Set `PLUGIN = ActionFiguresTypePlugin` at module level

### 4.4 Generic type plugin

- [ ] Write `plugins/types/generic.py` — minimal fallback plugin with basic
  condition vocabulary (Mint / Good / Poor) and no extra fields
- [ ] Used when no specific type plugin is selected

### 4.5 Manual source plugin

- [ ] Write `plugins/sources/manual.py` — `ManualSourcePlugin` with
  `supports_browse = False`, `supports_search = False`, all fetch methods
  returning empty lists or raising `NotImplementedError`
- [ ] This is the always-available fallback source; its existence confirms the
  plugin system works

### 4.6 Wire type plugin into Line creation

- [ ] "New Line" dialog: populate the collection type dropdown from `TYPE_PLUGINS`
  instead of a hard-coded list
- [ ] Store the selected type plugin `id` on the line record (`type_plugin_id`
  column — add to schema)
- [ ] When loading the detail panel for an item, use the line's type plugin to
  determine which condition vocabulary and extra fields to show

**Phase 4 test:** Restart app — console shows "Loaded type plugin: action_figures",
"Loaded type plugin: generic", "Loaded source plugin: manual". Create a new Line
and see "Action Figures" and "Generic" in the type dropdown. Select Action Figures
— condition dropdown in the detail panel shows C-10, C-9.5, etc. instead of Mint/
Near Mint/Good/Poor.

---

## Phase 5 — Images and Local Cache

**Deliverable:** Items can have images. A catalog image can be added manually by
dragging a file onto the detail panel or via a file picker. Personal photos can be
added separately. Images are stored in the local cache folder and shown as
thumbnails. The placeholder image is replaced.

---

### 5.1 Image cache manager

- [ ] Write `core/image_cache.py` — functions:
  `cache_image_from_url(url)` → returns local path (downloads, saves as MD5 hash
  of URL, generates 256×256 thumbnail)
  `cache_image_from_file(path, item_id)` → copies to cache, generates thumbnail
  `get_thumbnail_path(url_or_hash)` → returns local thumbnail path if cached
- [ ] Use Pillow for all image operations
- [ ] Store in `%APPDATA%\FigureArchive\collections\[name]\image_cache\`

### 5.2 Display catalog image in detail panel

- [ ] Replace the grey placeholder with a `QLabel` that shows the primary_image
  thumbnail if one exists
- [ ] Add a "Set Image" button below it — opens a file picker (jpg/png/gif)
- [ ] On selection, copy to cache and update `items.primary_image`

### 5.3 Image carousel for multiple catalog images

- [ ] Write `ui/image_carousel.py` — a horizontal strip of thumbnail buttons;
  clicking one sets it as the large preview image in the detail panel
- [ ] Add / remove images via `+` button and right-click > Remove
- [ ] Images stored in `item_images` table

### 5.4 Personal photos section

- [ ] Separate section in the detail panel below catalog images: "Your Photos"
- [ ] Same carousel UI but backed by `personal_photos` table
- [ ] Photos stored in `personal_photos/[item_uuid]/` (never in `image_cache/`)
- [ ] Add by file picker or drag-and-drop onto the section

### 5.5 Thumbnails in checklist rows

- [ ] Load the primary_image thumbnail (48×48) into each checklist row
- [ ] Show a grey square placeholder if no image; load thumbnails asynchronously
  (use a `QThread` or `QRunnable` so the UI doesn't freeze)

**Phase 5 test:** Select Optimus Prime. Drag an image file onto the catalog image
area — it appears in the detail panel and as a small thumbnail in the checklist
row. Add a second image via the + button. Add a personal photo. Quit and relaunch —
all images still appear.

---

## Phase 6 — First Source Plugin (Figure Realm)

**Deliverable:** An Import dialog lets you browse Figure Realm by manufacturer and
series. Selecting a series and clicking Import fetches all figures in that series
and adds them to the database as items, with images cached locally. A progress
bar shows the download. This is the first real network operation.

---

### 6.1 HTTP session helper

- [ ] Write `core/http_session.py` — a `requests.Session` with a browser-like
  User-Agent header, configurable timeout, and a `rate_limited_get(url, delay)`
  method that enforces a minimum delay between requests

### 6.2 Figure Realm source plugin skeleton

- [ ] Write `plugins/sources/figurerealm.py` — subclasses `SourcePlugin`
- [ ] `id = "figurerealm"`, `rate_limit_seconds = 2.0`,
  `supports_browse = True`, `supports_search = True`
- [ ] Implement `get_franchises()` — fetches `?action=manlist`, parses
  manufacturer list, returns `FranchiseData` objects
- [ ] Implement `get_lines(franchise)` — fetches `?action=manserieslist&id=N`,
  returns `LineData` objects
- [ ] Implement `get_items(line, wave=None)` — fetches
  `?action=seriesitemlist&id=N`, parses figure rows, returns `ItemData` objects
- [ ] Implement `get_item_detail(item)` — fetches individual figure page,
  parses accessories and additional images

### 6.3 Import engine

- [ ] Write `core/import_engine.py` — given a `SourcePlugin`, a `LineData`, and
  a target `line_id` in the DB:
  1. Call `plugin.get_items(line_data)` to get item list
  2. For each item: check if it exists (match on `source_key` + `line_id`); if
     yes update catalog fields; if no insert it
  3. Call `plugin.get_item_detail(item)` for each item (rate-limited)
  4. Download and cache all images
  5. Never touch `collection_entries` or `personal_photos`
  6. Write a row to `import_log` on completion
  7. Emit progress signals: `progress_updated(current, total, message)`

### 6.4 Import progress dialog

- [ ] Write `ui/import_progress_dialog.py` — `QDialog` with:
  - A `QProgressBar`
  - A status label ("Fetching item 23 of 187: Bumblebee")
  - A Cancel button that sets a flag the import engine checks between items
  - Connects to import engine's `progress_updated` signal
- [ ] Import runs in a `QThread` so the UI stays responsive

### 6.5 Import dialog (browse UI)

- [ ] Write `ui/import_dialog.py` — `QDialog` with:
  - Source selector dropdown (populated from `SOURCE_PLUGINS`)
  - A `QTreeWidget` showing franchises > lines (populated lazily when expanded)
  - An Import button (enabled when a line is selected)
  - A search bar (for later phases)
- [ ] Selecting a source and expanding the tree triggers `get_franchises()` and
  `get_lines()` calls
- [ ] Clicking Import opens the progress dialog and starts the import engine in a
  thread

### 6.6 Wire Import into main UI

- [ ] "Import Line" button in the sidebar (and File > Import menu item) opens the
  Import dialog
- [ ] On successful import, refresh the sidebar tree (new franchise/line appear if
  they were created) and load the imported line's checklist

**Phase 6 test:** Open Import dialog, select Figure Realm, expand Hasbro >
Transformers > Generation 1. Click Import. Watch the progress bar count up.
After completion: 100+ figures appear in the checklist, grouped by wave, most
with thumbnail images. Ownership checkboxes all unchecked (newly imported).

---

## Phase 7 — Search, Filter, and Grid View

**Deliverable:** A search bar filters the current checklist in real time. A filter
panel lets you narrow by ownership status, type, condition, flags, and tags. A
Grid view button switches the checklist to a card grid showing large images.

---

### 7.1 Search bar

- [ ] Add a `QLineEdit` search bar above the checklist
- [ ] On text change (debounced 300ms), filter the displayed items by name
  (case-insensitive substring match)
- [ ] Show result count ("47 of 187 items")

### 7.2 Filter bar

- [ ] Add a filter row below the search bar with dropdowns/buttons:
  - Ownership: All / Owned / Not Owned / Wanted / Sold
  - Type: All / Figure / Vehicle / Playset / Accessory / Gift Set
  - Flags: Favorites only / Needs Repair / On Display / Grail
  - Tags: multi-select dropdown of all tags
- [ ] Filters are applied additively (AND logic)
- [ ] "Clear Filters" button resets all

### 7.3 Global search

- [ ] Add a global search bar in the main toolbar (separate from the per-line
  search bar)
- [ ] Searches across all franchises and lines simultaneously
- [ ] Results list shows item name + franchise > line breadcrumb
- [ ] Clicking a result navigates to that line in the sidebar and selects the item

### 7.4 Grid view

- [ ] Write `ui/grid_view.py` — a `QScrollArea` containing a `QGridLayout` of
  item cards
- [ ] Each card: large image (128×128), item name below, status badge overlay
- [ ] Card size toggle: Small (4 cols) / Medium (3 cols) / Large (2 cols)
- [ ] Clicking a card opens the detail panel for that item
- [ ] Toggle between List and Grid via a button in the toolbar

### 7.5 Special sidebar views

- [ ] Add fixed views above the franchise tree in the sidebar:
  - All Items (shows every item across all lines)
  - Owned (filters to owned only)
  - Wanted (filters to wanted)
  - Grails (filters to grail-flagged items)
  - Favorites
  - Needs Repair
- [ ] These use the same checklist/grid view, just with a global filter applied

**Phase 7 test:** With 100+ figures imported: type "prime" in search — list
narrows to matching names. Set filter to "Owned" — shows only checked items. Click
Grid view — see image cards. Click a card — detail panel opens. Click "Grails" in
sidebar — shows empty (no grails set yet). Mark Optimus as a Grail via the
priority dropdown — it now appears in the Grails view.

---

## Phase 8 — eBay Auction Import

**Deliverable:** Paste an eBay listing URL into the app. The plugin fetches the
listing data, presents a mapping dialog, and adds the item to the collection with
all images and auction metadata stored. Also works to add images to an existing
wishlisted item.

---

### 8.1 eBay auth helper

- [ ] Write `core/ebay_auth.py` — handles OAuth2 Client Credentials flow;
  stores App ID + Client Secret in app config; auto-refreshes the token when
  it expires (2-hour TTL)
- [ ] First-run: prompt user to enter their eBay App ID and Client Secret
  (stored in `config.json`, never in the DB)

### 8.2 eBay auction source plugin

- [ ] Write `plugins/sources/ebay_auction.py`
- [ ] `supports_url_import = True`; `supports_browse = False`
- [ ] Implement `import_from_url(url)` — extracts the eBay item ID from the URL,
  calls Browse API `getItem`, returns an `ItemData` populated with: title,
  description, all image URLs, price, condition label, condition notes, seller
  username, listing URL
- [ ] If the API returns no result (ended listing), fall back to scraping the
  listing page directly

### 8.3 Auction mapping dialog

- [ ] Write `ui/ebay_import_dialog.py` — shown after the plugin returns data:
  - Shows listing title, price, condition, and first image
  - "Map to existing item" search box (search your DB for a match)
  - "Create new item" option (pre-fills name from listing title)
  - Checkboxes: "Set as Owned", "Use listing price as Paid Price",
    "Import all images", "Log auction details"
  - Franchise / Line selectors (if creating new)
- [ ] On confirm: write item (new or update existing), cache all images,
  write `auction_log` row, optionally set ownership + paid price

### 8.4 "Add eBay Listing" in detail panel

- [ ] Add an "Add eBay Listing" button to the detail panel (in the images section)
- [ ] Opens a small dialog: paste URL → fetches → adds images to `item_images`
  and logs to `auction_log` with `status = "reference"`

### 8.5 Auction log viewer

- [ ] A small "Auction History" collapsible section at the bottom of the detail
  panel showing past `auction_log` rows for this item: date, price, seller, status

**Phase 8 test:** Find a completed eBay listing for a G.I. Joe figure. Paste the
URL via File > Import from eBay URL. See the mapping dialog with the listing data.
Create a new item, set as Owned, import images, log the auction. The figure appears
in the checklist with images and a green Owned badge. Detail panel shows auction
history row.

---

## Phase 9 — Export and Statistics

**Deliverable:** Right-click a Line and export a PDF checklist. View a statistics
screen showing collection totals and completion bars. Export the full collection
to CSV.

---

### 9.1 Collection statistics screen

- [ ] Write `ui/statistics_view.py` — accessible from View menu or Home screen
- [ ] Shows:
  - Total items in library / total owned / total wanted
  - Breakdown by franchise: items / owned / completion % (with progress bar)
  - Breakdown by item type
  - Total paid (sum of `paid_price`)
  - Total estimated value (sum of `estimated_value`)

### 9.2 PDF checklist export

- [ ] Write `core/export_pdf.py` — uses WeasyPrint to render a checklist:
  - One row per item: checkbox column, name, year, optional thumbnail
  - Wave separator rows
  - Options: include thumbnails, unowned only, owned status column, page size
- [ ] Wire to right-click > Export Checklist as PDF on a Line in the sidebar

### 9.3 CSV export

- [ ] Write `core/export_csv.py` — exports current view (or full collection) as
  CSV with all fields (catalog + personal data)
- [ ] File > Export to CSV

### 9.4 Collection backup

- [ ] File > Backup Collection — copies `.db` + `personal_photos/` to a
  timestamped zip at a user-selected path
- [ ] `image_cache/` is excluded (re-downloadable)

**Phase 9 test:** Export Generation 1 as a PDF checklist — opens a formatted PDF
with wave separators and checkboxes. View statistics — see correct counts and
completion bars. Export to CSV — open in a spreadsheet and confirm all fields present.

---

## Phase 10 — Polish and Settings

**Deliverable:** A Settings screen. Re-import / refresh a line from source.
Home screen with recent activity and completion bars. Batch operations on multiple
selected items. Quick-mark mode.

---

### 10.1 Settings screen

- [ ] Write `ui/settings_view.py` — tabbed settings:
  - **General:** theme (dark/light), default collection folder, auto-save delay
  - **Sources:** per-plugin config (API keys, rate limits); show/disable plugins
  - **Tags:** create, rename, recolor, delete tags; show usage count per tag
  - **Image Cache:** show cache size, "Clear Cache" button, re-download missing
    images button
  - **eBay:** App ID and Client Secret fields

### 10.2 Re-import / refresh from source

- [ ] Right-click Line > Refresh from Source
- [ ] Runs import engine on the line again; updates catalog fields on existing
  items; adds new items; marks orphaned items (in DB but not in source) with a
  `source_orphan = 1` flag and shows a small indicator badge in the checklist
- [ ] Never touches personal data

### 10.3 Home screen

- [ ] Write `ui/home_screen.py` — shown on startup before a line is selected:
  - Total counts: items / owned / wanted / lines
  - Completion progress bars per line (top 5 or all, scrollable)
  - Recent activity feed (last 10 changes from a new `activity_log` table)
  - Buttons: Browse Collection, Import New Line, Search All

### 10.4 Batch operations

- [ ] Multi-select in checklist (`Ctrl+click`, `Shift+click`)
- [ ] Right-click selection → context menu: Mark all Owned, Mark all Wanted,
  Add Tag, Set Condition, Remove from Collection
- [ ] Edit > Select All selects all items in the current view

### 10.5 Quick-mark mode

- [ ] Toolbar toggle: Quick-mark Mode
- [ ] While active, clicking anywhere on a row (not just the checkbox) toggles
  owned status
- [ ] Visual indicator that quick-mark mode is on (tinted toolbar or banner)

### 10.6 UPC lookup

- [ ] In the "Add Item" dialog and the detail panel, add a UPC field with a
  "Lookup" button
- [ ] Calls UPCitemdb (100 req/day free, no key) with the UPC; if found,
  pre-fills name, brand, category, images
- [ ] Stores the UPC on the item record

**Phase 10 test:** Open settings, add an eBay App ID. Re-import Generation 1 —
see the progress dialog, confirm no personal data was changed on Optimus. Enable
Quick-mark mode and rapidly click rows to toggle owned. Select 10 items, right-
click > Mark all Wanted. Open statistics — counts updated correctly.

---

## Phase 11 — Additional Source Plugins

**Deliverable:** Figure Archive scraper works. Comics source (Metron) works.
Each is a standalone plugin dropped into `plugins/sources/` with no changes to core.

---

### 11.1 Figure Archive plugin

- [ ] Write `plugins/sources/figure_archive.py`
- [ ] Parse `/indexR.aspx` for manufacturer list
- [ ] Parse `/toyline.aspx?toylineID=N` for line checklists
- [ ] Parse individual item pages for name, image, accessories
- [ ] `rate_limit_seconds = 2.0`

### 11.2 Metron comics plugin

- [ ] Write `plugins/sources/metron.py`
- [ ] Uses `mokkari` Python library
- [ ] Wraps `series` as Lines, `issues` as Items
- [ ] `compatible_type_ids = ["comics"]` — only appears as a source option when
  the Line's type is Comics

### 11.3 BoardGameGeek plugin

- [ ] Write `plugins/sources/boardgamegeek.py`
- [ ] Uses BGG XML API2 via `boardgamegeek2` library
- [ ] Wraps game collections as Lines, individual games as Items
- [ ] `compatible_type_ids = ["board_games"]`

### 11.4 Discogs plugin

- [ ] Write `plugins/sources/discogs.py`
- [ ] Uses `python3-discogs-client`
- [ ] Artists/labels as Franchises, release series as Lines, releases as Items
- [ ] `compatible_type_ids = ["vinyl"]`

### 11.5 PriceCharting plugin

- [ ] Write `plugins/sources/pricecharting.py`
- [ ] `supports_price_lookup = True`; `supports_browse = False`
- [ ] `get_price(item)` — calls PriceCharting API by title or UPC, returns price
  tiers (loose, complete, new, graded)
- [ ] Stores result as a `price_snapshot` (new table) with timestamp
- [ ] "Check Price" button in detail panel triggers this

**Phase 11 test:** Create a Comics franchise and a line with type "Comics".
Open Import dialog — only Metron appears as a source option (Figure Realm is
hidden because it's incompatible with the Comics type). Import a Marvel series
via Metron — issues appear as items. Check Price on a Figure Realm figure —
PriceCharting data appears.

---

## Phase 12 — Shopping List Export and REST API Foundation

**Deliverable:** Export a grail/wantlist as a portable HTML file viewable on a
phone. A basic FastAPI server can be started from the app and serves a read-only
JSON endpoint of the collection (foundation for future mobile PWA).

---

### 12.1 Shopping list export

- [ ] File > Export Shopping List — generates a single self-contained HTML file
- [ ] Contains: all Grail and Wanted items, with name, franchise/line, thumbnail
  (base64 embedded), notes, any reference images
- [ ] No external dependencies — works offline in any browser
- [ ] Suitable for putting on a phone via Google Drive, AirDrop, email, etc.

### 12.2 FastAPI server (optional, user-activated)

- [ ] Write `core/api_server.py` — a FastAPI app with endpoints:
  `GET /collection` — summary stats
  `GET /items?status=wanted` — filtered item list
  `GET /items/{id}` — item detail
  `GET /lines` — all lines
- [ ] Start/stop from Settings > Enable Local API Server (toggle + port field)
- [ ] Server runs in a background thread; does not block the Qt UI
- [ ] Serves on `localhost:PORT` by default; user can bind to LAN interface for
  Tailscale/home network access
- [ ] No auth on localhost; optional simple token for LAN access

**Phase 12 test:** Export shopping list — open the HTML file on a phone browser,
see grail items with images. Enable the API server on port 8080. Navigate to
`http://localhost:8080/items?status=wanted` in a browser — see JSON list of
wanted items.

---

## Summary — Phase Deliverables

| Phase | What you can do at the end |
|---|---|
| 1 | Launch app, create franchises and lines, data persists |
| 2 | Add items manually, check them off as owned, see wave separators |
| 3 | Click items, edit all personal data, auto-saves, tags work |
| 4 | Plugin system loads, type plugins change condition vocabulary |
| 5 | Add images to items, see thumbnails in checklist |
| 6 | Import a full toyline from Figure Realm with images |
| 7 | Search and filter the collection, toggle grid view, Grails view |
| 8 | Paste an eBay URL to log a won auction and its images |
| 9 | Export PDF checklists, view stats, export CSV |
| 10 | Settings, refresh from source, batch ops, quick-mark mode |
| 11 | Comics, board games, vinyl sources work as standalone plugins |
| 12 | Shopping list HTML export, optional local REST API |
