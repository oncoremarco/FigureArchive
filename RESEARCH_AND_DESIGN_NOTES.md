# FigureArchive — Research & Design Notes

This document consolidates pre-implementation research and design decisions.
It supplements the application spec (`figure_archive_spec.md`) and should be
read alongside it. No code has been written yet.

---

## Table of Contents

1. [Reference Projects](#1-reference-projects)
2. [Architecture Decisions](#2-architecture-decisions)
3. [Collection Model](#3-collection-model)
4. [Plugin System Design](#4-plugin-system-design)
5. [Data Sources & APIs](#5-data-sources--apis)
6. [eBay Integration Approach](#6-ebay-integration-approach)
7. [Item State & Flag Design](#7-item-state--flag-design)
8. [UI Direction](#8-ui-direction)
9. [Open Questions & Future Work](#9-open-questions--future-work)

---

## 1. Reference Projects

### Primary Codebase Reference — OpenNumismat

- **Repo:** https://github.com/OpenNumismat/open-numismat
- **Stack:** PySide6 + SQLite, GPL-3.0, actively maintained (April 2026 release)
- **Why it matters:** The closest open-source analog found. Designed as a general
  collectibles tracker (coins by default; explicitly supports stamps, postcards,
  trading cards, and more). Has: image management, barcode scanning via zxing-cpp,
  import/export (Excel, Tellico XML, CSV), thumbnail generation, PyInstaller
  packaging, Flathub distribution.
- **What to study:** Its modular import/export pipeline, SQLite schema, image
  cache management, and how it handles extensibility beyond coins.
- **What not to copy:** Its coin-specific field set and UI vocabulary — our schema
  should be plugin-defined, not hard-coded.

### Plugin Architecture Reference — ComicTagger / comictalker

- **Repo:** https://github.com/comictagger/comictagger
- **License:** Apache-2.0
- **Why it matters:** The `comictalker` subsystem is the cleanest open-source
  implementation of a "fetch metadata from external sources" plugin pattern in a
  Python/Qt desktop app. It separates: file I/O layer / UI + business logic /
  external API sources (plugins).
- **What to adopt:** This three-way split and the plugin registration/discovery
  pattern. Our "source plugins" and "collection type plugins" should follow the
  same structure.

### UI Layout Reference — TagGUI / Calibre

- **TagGUI** (https://github.com/jhc13/taggui): 1,300 stars, PySide6.
  Best three-pane layout implementation found: item list → image viewer → attribute
  panel, with filter bar and tag aggregate pane. The Qt model/view separation is
  clean and inspectable.
- **Calibre** (https://github.com/kovidgoyal/calibre): Gold standard for
  sidebar + sortable list + detail panel. Study for UX patterns and its SQLite
  abstraction layer; do not fork (C extensions, too complex).

### Feature Specification Reference — Tellico

- **Repo:** https://github.com/KDE/tellico (C++/KDE, cannot use as a base)
- **Why it matters:** The most feature-complete general collectibles manager that
  exists. Supports: books, videos, music, coins, stamps, trading cards, comics,
  wine, board games. Most important architectural idea: **fully customizable field
  schema per collection type**. This is the model our collection type plugin system
  should implement.
- OpenNumismat can import Tellico XML — useful for users migrating.

### Data Layer Reference — Beets dbcore

- **Repo:** https://github.com/beetbox/beets
- **Why it matters:** Not a Qt app, but its `dbcore` library (SQLite abstraction
  with typed fields, query language, transactions: `Library → Database → SQLite`)
  is the best Python collection-database architecture pattern found. Worth studying
  before writing our own ORM layer.

---

## 2. Architecture Decisions

### Core principle: the app is a shell, plugins are the substance

The application core should be as thin as possible. It provides:
- The window chrome and navigation skeleton
- The SQLite database engine and schema foundation
- The plugin loader (for both collection types and data sources)
- The import engine (rate limiting, image caching, deduplication, logging)
- The personal data layer (ownership, condition, notes, photos — never overwritten)
- Generic UI components (checklist view, detail panel, search/filter bar)

**The app core must not contain:** site-specific scraping code, field definitions
for specific collectible types, or hard-coded assumptions about what fields an
item has. All of that lives in plugins.

This means:
- A Transformers G1 figure and a vinyl record and a comic issue are all just
  "Items" to the core — their field schemas come from their collection type plugin
- Adding a new data source (a new website or API) requires only adding a new
  source plugin file, no changes to core
- Adding a new collectible domain (e.g. Funko Pops, LEGO sets, video games) requires
  only adding a new collection type plugin

### Two plugin axes

**Axis 1 — Collection Type Plugins** (define what fields an item has):
- `plugins/types/action_figures.py`
- `plugins/types/comics.py`
- `plugins/types/vinyl.py`
- `plugins/types/board_games.py`
- `plugins/types/video_games.py`
- `plugins/types/trading_cards.py`
- `plugins/types/generic.py` (fallback with minimal fields)

Each type plugin declares: its display name, its item fields (typed, with labels
and valid values), its condition vocabulary, its completeness model, and which
source plugins it is compatible with.

**Axis 2 — Source Plugins** (define how to fetch catalog data):
- `plugins/sources/figurerealm.py`
- `plugins/sources/figure_archive.py`
- `plugins/sources/ebay_auction.py`
- `plugins/sources/pricecharting.py`
- `plugins/sources/metron.py` (comics)
- `plugins/sources/boardgamegeek.py`
- `plugins/sources/discogs.py`
- `plugins/sources/igdb.py`
- `plugins/sources/upcitemdb.py`
- `plugins/sources/manual.py` (always available)

Source plugins declare which collection types they can provide data for, and
whether they support browse, search, direct URL import, or UPC lookup.

### Schema approach

The SQLite schema has two layers:

**Layer 1 — Core schema (defined by the app):** franchises, lines, waves, items
(with a fixed set of universal fields: id, name, source_key, source_url,
primary_image, sort_order, etc.), collection_entries (ownership, condition,
personal data), import_log, tags, personal_photos.

**Layer 2 — Extended fields (defined by collection type plugins):** A key-value
store (`item_fields` table) or a per-type JSON blob column on items, allowing
type plugins to attach arbitrary typed fields without schema migrations.

This is the Tellico model: the core item is generic, the rich type-specific
metadata is a plugin-defined extension.

---

## 3. Collection Model

### Multiple collections AND mixed-type collections

The application supports two usage modes, which are not mutually exclusive:

**Mode A — Single mixed collection:** One database (`my_collection.db`) containing
action figures, comics, vinyl, board games, and whatever else the user owns. All
tracked in one place. The sidebar groups by franchise/line as normal; the type
badge on each item (Figure / Comic / Record / Game) distinguishes them visually.
Good for users who want to see their entire personal archive in one view.

**Mode B — Separate focused collections:** Multiple `.db` files, one per domain
or focus area. `transformers.db`, `vinyl.db`, `silver_age_comics.db`. Opened via
File > Open Collection or from a collection switcher on the home screen. Good for
users who want clean separation, or who share a machine with family members with
different collections.

**The app supports both simultaneously** — a user might have a mixed
`household_collection.db` and also a dedicated `grails.db` tracking their most
prized items across categories. The collection switcher in the UI makes opening
any `.db` a one-click action, and the home screen shows recently opened
collections.

### Collection type is per-Line, not per-item

When creating or importing a Line, the user selects its collection type (action
figures, comics, vinyl, etc.). All items in that Line share the same type plugin.
This keeps the data model clean: you don't mix figure fields and vinyl fields
within the same line, but you can have a Transformers G1 line (figures) and a
Transformers Soundtrack line (vinyl) within the same Transformers franchise.

### Nested groups within a Line (self-nesting "waves")

The original model had a single flat grouping level under a Line ("waves").
Real toylines need deeper, variable nesting, and the "primary axis" differs:

- **TF G1** (tfwiki): `1984 → Autobot Cars / Decepticons / Mini-Vehicles`,
  `1985 → Dinobots / Insecticons / …` — a year level *and* a subgroup level.
- **Mighty Max**: `Doom Zones → Horror Heads → …` — series → sub-series.
- **McDonald's Changeables**: `1987 set / 1989 set` — year *is* the subgroup.

**Decision:** generalise the flat wave level into a **self-nesting Group** (the
`waves` table gains a nullable self-referencing `parent_id`). Depth is optional
and arbitrary — a simple line stays one flat level; G1 nests two; Mighty Max can
nest as deep as needed. An item attaches to a leaf group, or directly to the
Line when ungrouped.

**Where the nesting is shown:** *inside the checklist* as indented headers, not
as expandable nodes in the left sidebar. This keeps the "whole toyline as one
scrollable completion checklist" mental model, mirroring the layout of the wiki
pages collectors reference. The sidebar stays Franchise → Line. (Promoting
groups into the sidebar for very large collections remains a later option; the
data model is identical either way.)

**Cross-cutting axes stay as tags.** A figure is simultaneously "1985" and "a
Dinobot." A strict tree forces one parent; the other axis (faction, scale,
assortment) is expressed with item **tags**, which already exist, so you can
filter "all Dinobots across all years" without fighting the hierarchy.

---

## 4. Plugin System Design

### Collection Type Plugin interface (sketch — not final code)

```
CollectionTypePlugin:
    id: str                          # "action_figures", "comics", "vinyl"
    name: str                        # "Action Figures"
    item_fields: list[FieldDefinition]   # domain-specific fields
    condition_vocabulary: list[str]  # ["C-10", "C-9", ...] or ["Mint", "NM", ...]
    packaging_states: list[str]      # ["MOC", "MIB", "MISB", "Loose", ...]
    has_accessory_list: bool         # whether items track accessories as a checklist
    compatible_source_ids: list[str] # which source plugins provide data for this type
```

Field types: text, integer, float, boolean, date, dropdown (with defined options),
multi-select, url.

### Source Plugin interface (from spec, confirmed)

Per `figure_archive_spec.md` Section 6, with the following additions:

- `supports_url_import: bool` — can process a single URL pasted by the user
  (e.g., a specific eBay listing, an auction won, a product page)
- `supports_upc_lookup: bool` — can return item data given a UPC/EAN barcode
- `supports_price_lookup: bool` — can return current or historical pricing data
- `compatible_type_ids: list[str]` — which collection types this source covers

### Plugin discovery

Both plugin axes use the same `importlib` scan pattern. The loader looks for
`.py` files in `plugins/types/` and `plugins/sources/`. Each file must expose a
`PLUGIN = MyPluginClass` at module level. No registration step, no config file
update — drop the file in, restart the app.

---

## 5. Data Sources & APIs

### Action Figure Registries

All sites below block non-browser user-agent strings and return 403. Any scraper
must spoof browser headers and respect crawl delays. No public Python scrapers
for any of these sites exist as of this research — this code is net-new.

| Site | Method | URL Pattern | Richest Data | Notes |
|---|---|---|---|---|
| **figurerealm.com** | Scraping | `?action=seriesitemlist&id=N` | Name, year, item#, accessories, images | Best URL structure; fully parameterized numeric IDs |
| **figure-archive.net** | Scraping | `/toyline.aspx?toylineID=N` | Name, image, assortment, year | 50K+ figures, 62K+ images; ASP.NET |
| **theafdb.com** | Scraping | Slug URLs | Name, brand, toyline, character, vehicles | Newest (2023); most comprehensive scope |
| **transformerland.com** | Scraping | `/wiki/transformers/g1/` etc. | Tech specs, accessories, bios, variants, price, instructions | Richest per-figure data; Transformers only |
| **HobbyDB** | REST API | Partner agreement required | Items, values, subjects, for-sale listings | Most API-forward; contact required |
| **MyFigureCollection.net** | Partial API (v4) | `/api.v4.php` | Anime figures only | Western figures not covered |

### PriceCharting (pricecharting.com)

- Covers: video games (primary focus), but also TCG cards, comics, toys/action
  figures, vinyl, board games — a broad collectibles price guide
- Has a documented API (paid, tiered pricing) returning: title, id, loose price,
  complete price, new price, graded price, box-only price, manual-only price,
  image URL
- Also has a free web interface searchable by title and UPC
- **Integration approach:** Source plugin for price lookups on owned or wishlisted
  items. When a user views an item, an optional "Check Price" action calls the
  PriceCharting API and stores the result as a `price_snapshot` in the DB (with
  timestamp) — never overwriting the user's own `estimated_value` field.
- URL import is also viable: user pastes a PriceCharting product URL, plugin
  extracts product ID and fetches structured data

### Comic Databases

| Service | Free | Auth | Rate Limit | Python Library | Use |
|---|---|---|---|---|---|
| **Metron** | Yes | Free account | 20/min, 5K/day | `mokkari` (official, async) | Primary comics source |
| **ComicVine** | Yes | Free key | 200 req/hr | `simyan` (Metron Project) | Fallback / supplement |
| **GCD** | Dump | Free account | N/A | `gcd-utils` | Offline enrichment |
| **Marvel API** | Yes | Free key | 3,000/day | `esak` (Metron Project) | Marvel-specific; attribution required |

### Other Domain APIs

| Domain | Service | Auth | Python Library |
|---|---|---|---|
| Board games | BGG XML API2 | None | `boardgamegeek2` |
| Vinyl / music | Discogs API | Free app key | `python3-discogs-client` (official) |
| Video games | IGDB | Twitch OAuth | `igdb-api-v4` (official) |
| Any UPC | UPCitemdb | None (100/day free) | raw `requests` |
| Any UPC (fallback) | Open Products Facts | None | raw `requests` |

### Preformatted / openly-licensed bulk datasets (no-scrape path)

Researched 2026-06-14 in response to "can we get preformatted toyline data without
scraping?" Live GitHub search + prior knowledge. **Verdict: no clean, comprehensive
open *action-figure* dataset exists** — GitHub search for action-figure datasets
returns zero relevant results, which is exactly why the fan registries (and
scraping) are the usual route. But several adjacent collectible domains the app
already supports as *types* have excellent openly-licensed bulk data:

| Source | Domain | License | Bulk access | Bundle-able? |
|---|---|---|---|---|
| **Wikidata** | Toylines + *notable* figures, broad | **CC0 (public domain)** | SPARQL endpoint + REST + full dumps | **Yes — best general source** |
| **Discogs** | Vinyl / music | **CC0** monthly data dumps (XML) | Direct download | Yes |
| **MusicBrainz** | Music | **CC0** core data + dumps | Direct download | Yes |
| **Rebrickable** | LEGO sets/parts | Free CSV downloads (attribution) | Direct CSV | Yes, with credit |
| **GCD** | Comics | Downloadable SQL dumps (attribution) | Account + dump | Yes, with credit |
| **DBpedia** | Wikipedia infoboxes (toylines) | CC-BY-SA (copyleft) | SPARQL + dumps | Yes, but share-alike |

**Key takeaways:**
- **Wikidata is the one broad source we can freely bundle** (CC0). Coverage of
  *individual* vintage action figures is patchy, but toylines and notable figures
  (Transformers, Star Wars, MOTU, G.I. Joe) are present, with properties like
  manufacturer (P176), inception (P571), publication date (P577), part-of-series
  (P179). A one-time SPARQL query (run outside the app) can produce a CC0 catalog.
- For action figures specifically, the realistic no-scrape path is **curated +
  Wikidata-derived "seed packs"**, not a turnkey download.

**Proposed mechanism — "data packs" (fully offline, no network in the app):**
Define a versioned **JSON import format** mirroring our model
(`franchise → line → groups → items`, with source attribution + license fields).
Packs can be produced from *any* source (a one-time Wikidata SPARQL export, hand
curation, or community contributions) and dropped into the app. The app ships a
couple of CC0-derived starter packs and an "Import Data Pack…" action. This:
- needs **zero live scraping** — unblocked even in the network-restricted dev env,
- reuses the same import/attribution plumbing the deferred Phase 6 will need,
- lets the community grow catalog coverage without each user hitting any site.

This is the recommended near-term way to get "preformatted toyline data" in.

**Update (exhaustive sweep via `WebSearch`, 2026-06-14):** Direct page fetches are
blocked by the dev egress allowlist, but the `WebSearch` tool routes around it and
*does* work here, so live dataset hunting is possible. A full sweep of Kaggle,
Hugging Face, data.world, datahub.io and GitHub confirms: **every "toy dataset"
hit is a generic ML toy/example dataset or Amazon product scrape — none is an
actual action-figure catalog.** No turnkey dataset exists; confirmed.

Two additional no-scrape paths surfaced:
- **Fandom-hosted wikis offer official XML database dumps** (Special:Statistics →
  database download), licensed **CC-BY-SA**. Relevant: `transformers.fandom.com`
  (Teletraan I), `mightymax.fandom.com`, `kidsmeal.fandom.com`. These are bulk and
  official (no scraping), but the payload is **wikitext** (needs parsing) and the
  share-alike license means derived packs must carry attribution + CC-BY-SA.
- **tfwiki.net is independent MediaWiki** (not Fandom) → has `api.php` /
  `Special:Export`, but that's the deferred live-network path.

Net: bundle CC0 Wikidata as the primary seed; optionally enrich from Fandom XML
dumps (offline, with attribution) for lines Wikidata covers thinly.

### eBay API

- **Legacy APIs dead:** Finding API and Shopping API decommissioned February 2025.
  Do not use `ebaysdk` Python package.
- **Current API:** Browse API (REST). Python library: `ebay-rest` v1.1.4 (PyPI).
- **Production access:** Requires eBay Partner Network approval for Buy APIs.
  Develop in Sandbox first. Apply with honest personal-use description.
- **Rate limit:** 5,000 calls/day — sufficient for personal use.
- **Key data fields:** title, description, images, price, condition,
  conditionDescription, category, UPC, itemWebUrl.
- **Our integration approach:** See Section 6 — we do not use eBay's live search.
  We process individual auction URLs the user provides.

---

## 6. eBay Integration Approach

### Design decision: URL-based auction processing, not integrated search

Rather than building live eBay search into the app (which requires EPN approval
and ongoing API dependency), the eBay source plugin handles **individual listing
URLs** that the user provides.

This has several advantages:
- No EPN approval needed for processing a URL the user already has
- Simpler scope: the user knows what they bought or what they're looking at
- The data is exact (one specific listing) rather than approximate (search results)
- Works for completed/ended auctions as well as active ones

### Use Case A — Logging a won auction

The user won an eBay auction for a figure they didn't have in their collection.

Workflow:
1. User opens the import dialog, selects "eBay Auction URL"
2. Pastes the listing URL (can be a completed listing URL, `ebay.com/itm/...`)
3. The plugin fetches the listing via Browse API `getItem` (or scrapes if the
   listing has ended and the API no longer has it)
4. Extracted data: title, description, all images, seller, final price, condition,
   conditionDescription, listing URL, listing ID
5. App presents a "map to collection" dialog:
   - Match to an existing item in the DB, or create a new one
   - If creating: pre-fills name, images, description from the listing
   - Auto-sets ownership status to Owned
   - Pre-fills `paid_price` from the final sale price
   - Pre-fills `acquired_from` as "eBay" + seller username
   - Pre-fills `acquired_date` from the auction end date
   - Attaches all listing images to the item's `item_images` table (as catalog
     images, locally cached) — these become the item's photo record
6. The full auction metadata (listing ID, seller, final price, all image URLs, raw
   condition notes) is stored in a new `auction_log` table linked to the item
7. The item appears in the collection as owned, with the auction images as its
   primary images

### Use Case B — Appending images to a wishlisted or grail item

The user found an eBay listing for something they want and wants to save the
images and details to their wishlist entry.

Workflow:
1. User selects an existing wishlisted or grail item in their collection
2. In the detail panel, clicks "Add eBay Listing"
3. Pastes the listing URL
4. Plugin fetches images and listing details
5. Images are downloaded and cached, added to `item_images` for that item
6. Listing price is stored as a `price_snapshot` (with timestamp) — not overwriting
   `estimated_value`
7. The listing URL is stored as a reference in `auction_log` with status "reference"
   (not "won")

### Use Case C — Enriching an existing item

Same flow as B, applied to any item regardless of ownership status. Useful when
the primary source plugin didn't return good images and the user found better
ones on a specific eBay listing.

### auction_log table (addition to spec schema)

```sql
CREATE TABLE auction_log (
    id              TEXT PRIMARY KEY,
    item_id         TEXT NOT NULL REFERENCES items(id),
    listing_id      TEXT,               -- eBay item ID
    listing_url     TEXT,
    seller          TEXT,
    final_price     REAL,
    currency        TEXT DEFAULT 'USD',
    condition_label TEXT,               -- eBay condition string
    condition_notes TEXT,               -- seller's condition description
    auction_end_date TEXT,              -- ISO date
    status          TEXT,               -- "won", "reference", "watching"
    notes           TEXT,
    logged_at       TEXT NOT NULL       -- ISO datetime
);
```

---

## 7. Item State & Flag Design

### Ownership status enum

Extending the spec's current 4-value model:

| Value | Label | Description |
|---|---|---|
| 0 | Not Owned | Default for imported items |
| 1 | Owned | In collection |
| 2 | Sold / Traded | Was owned, no longer |
| 3 | Wanted | On wishlist |
| 4 | On Order | Purchased, not yet received |

### Wishlist priority tiers (applied when status = 3 or 4)

| Value | Label | Description |
|---|---|---|
| 0 | Watching | Aware of it, not actively pursuing |
| 1 | Wanted | Actively looking |
| 2 | Grail | Highest priority; first-class feature with dedicated UI view |

All current collection apps treat the wishlist as a flat unordered list.
Treating Grail as a first-class feature with its own sidebar view is a genuine
differentiator. The Grail view surfaces grail items across all lines/franchises
in one place, alongside any reference images or eBay listings the user has saved.

### Condition model (toy-specific — from collection type plugin)

**Figure condition:** C-10 / C-9.5 / C-9 / C-8 / C-7 / C-6 / C-5 and below
(or simplified Mint / Near Mint / Very Good / Good / Poor for non-vintage items)

**Box/package condition:** Same scale, tracked separately from figure condition.
A figure can be C-9 while its box is C-6. This dual-condition model is how
serious vintage toy collectors track items, and no current general app implements it.

**Packaging state (separate from condition grade):**
MOC (Mint on Card) / MIB (Mint in Box) / MISB (Mint in Sealed Box) / Loose /
Incomplete / Parts Only

The collection type plugin declares which vocabulary to use.

### Completeness model

- `is_complete` (boolean)
- `missing_accessories` (text or structured list)

When a source plugin returns an accessory list for an item, the detail panel
exposes a per-accessory checklist (Rebrickable model applied to figures). The user
checks off which accessories they have. The completeness badge on the item
derives from this checklist. This is a differentiating feature no general app offers.

### Boolean flags (on collection_entries)

| Flag | Type | Notes |
|---|---|---|
| `is_favorite` | boolean | Already in spec |
| `on_display` | boolean | Already in spec |
| `is_grail` | boolean | Tied to wishlist priority tier 2 |
| `needs_repair` | boolean | Broken or requires restoration work |
| `is_loaned` | boolean | Currently loaned to someone |
| `loaned_to` | text | Name of person item is loaned to |
| `is_for_sale` | boolean | Owned but listed/wanting to sell |
| `is_sealed` | boolean | Factory sealed / unopened |

`needs_repair` is a gap in all current collection apps. Vintage toy collectors
frequently track items that need cleaning, re-riveting, part replacement, or
paint touch-up. A dedicated "Needs Repair" filter view makes this actionable.

---

## 8. UI Direction

### Technology: PySide6 with CSS/QSS styling

The UI uses PySide6's Qt Style Sheets (QSS) — Qt's CSS-like styling system — to
produce a polished, theme-able interface rather than the default OS widget look.
QSS supports: colors, fonts, borders, padding, border-radius, gradients, and
state-based selectors (`:hover`, `:checked`, `:disabled`), which is sufficient
for a professional dark/light theme.

Key styling targets:
- A dark theme by default (common in collector community apps)
- Clean card-style item rows with rounded thumbnails
- Color-coded status badges (Owned = green, Wanted = blue, Grail = gold, Sold = grey)
- Wave/separator rows styled as full-width section headers
- Tag chips with per-tag color

Additional UI polish beyond QSS:
- Smooth scroll in lists (Qt's default is fine)
- Lazy-loading thumbnails (load on scroll, placeholder while loading)
- Debounced auto-save on text fields (1.5s, same pattern as Scratchpad noted in spec)

### Main window layout

Three-pane layout (Calibre / TagGUI model):

```
+------------------+---------------------+------------------+
| Sidebar          | Item List           | Detail Panel     |
| (franchise/line  | (checklist or grid) | (item info,      |
|  tree)           |                     |  personal data,  |
|                  |                     |  images, notes)  |
+------------------+---------------------+------------------+
| Filter / search bar (full width)                          |
+-----------------------------------------------------------+
```

The detail panel collapses when nothing is selected. On narrow screens, it slides
over the item list (overlay) rather than splitting.

### Sidebar

Collapsible franchise → line tree. Special views pinned above the tree:
- All Items
- Owned
- Wanted
- **Grails** (dedicated view — first-class)
- Favorites
- On Display
- **Needs Repair** (dedicated view)
- Recently Added

### Collection switcher

A collection-level picker on the home screen and in the File menu. Recently
opened collections appear as a list. Each collection shows: name, path, item
count, owned count, last opened date. Creating a new collection opens a wizard
(name, location, optional initial collection type).

---

## 9. Open Questions & Future Work

### Unresolved

- **PriceCharting API tier:** Need to evaluate cost for the level of use expected
  (personal app, on-demand price checks, not bulk). Free web scraping is a fallback
  if the API cost is prohibitive.

- **eBay completed listing access:** The Browse API's `getItem` works for active
  listings. For completed/ended auctions, we may need to scrape the item page
  directly (eBay keeps completed listing pages available for ~90 days). Need to
  confirm whether the Browse API returns ended-auction data.

- **Collection type plugin field storage:** Decide between: (a) a key-value
  `item_fields` table (flexible, queryable, verbose), (b) a JSON blob column on
  items (simple, not directly queryable), or (c) generated per-type tables
  (fastest queries, requires migration per plugin). Likely (a) or (b).

- **Barcode scanning hardware:** The spec mentions barcode scanning for future
  use. UPC lookup via UPCitemdb is confirmed free at 100/day. Worth confirming
  which Python barcode scanning library (zxing-cpp as in OpenNumismat, or
  pyzbar + OpenCV) is easier to package on Windows.

### Future integration candidates

- **Scryfall** (Magic: The Gathering cards) — excellent free API, well-documented,
  high image quality
- **Pokémon TCG API** — free, well-documented, covers all sets
- **TCGPlayer API** — trading card prices, broader TCG coverage
- **Entertainment Earth / Sideshow Collectibles** — retailer scraping for new
  release images and pre-order tracking (not a priority, but a natural extension)
- **ToyHuntr-style alerts** — when a grail item appears on eBay matching search
  criteria, notify the user. Requires background polling or webhook integration.
  Long-term feature.
- **Tellico XML import** — since OpenNumismat already supports this, users
  migrating from Tellico (the only other serious desktop collectibles tracker)
  should be able to bring their data in

### Mobile Companion (Android) — Long-term consideration

The primary use case is **out shopping**: checking your grail/wantlist, seeing
what you already own, and ideally marking something as acquired on the spot.
The constraint is local-first — no central cloud database.

Four realistic approaches, each with different tradeoffs:

---

**Option A — Desktop as local REST server + VPN tunnel (recommended long-term)**

The desktop app runs a lightweight embedded HTTP server (FastAPI is the natural
choice given Python) bound to localhost or the LAN interface. A native or web-
based Android client connects to it.

- **On home WiFi:** Phone connects directly by LAN IP (`http://192.168.x.x:PORT`).
  Full read+write access. No latency beyond LAN.
- **Out shopping (away from home WiFi):** Requires a VPN tunnel back to the home
  machine. Tailscale is the best option here — it is free for personal use,
  installs on both Windows and Android, creates a peer-to-peer WireGuard mesh with
  no central server holding your data (Tailscale's coordination server only handles
  key exchange, not traffic). Once Tailscale is set up, the desktop's local server
  is reachable at its Tailscale IP from anywhere in the world.
- **Android client options:**
  - A **Progressive Web App (PWA)** served by the desktop's HTTP server — no app
    to build or distribute. Phone opens a browser to the Tailscale IP. A
    mobile-optimized web UI (separate from the Qt desktop UI) lives in the same
    codebase. Works on any device with a browser.
  - A **native Android app** (Kotlin or Flutter) that speaks to the REST API. More
    work, better native UX, can work offline with local SQLite cache.
- **No data ever touches a third-party server.** Tailscale's role is purely
  routing; the data path is phone ↔ home PC directly (encrypted WireGuard).
- **Effort:** Medium. Requires: adding a FastAPI server layer to the desktop app,
  designing a REST API surface, and building a mobile-optimized web UI or native
  app. The REST API is also useful for scripting and future integrations.

---

**Option B — File sync via Syncthing**

Desktop exports a snapshot of the collection (SQLite file or a derived JSON/CSV)
to a folder that Syncthing watches. Syncthing replicates it to the phone without
going through any cloud provider.

- **Advantages:** Trivially simple on the desktop side (just write a file).
  Syncthing is mature, open-source, and genuinely peer-to-peer.
- **Disadvantages:** Read-only by default — edits on the phone (marking something
  owned, adding a note while at the store) are hard to sync back without conflict
  resolution logic. The snapshot can be stale if the desktop app wasn't running
  recently. Requires Syncthing to be installed and configured separately.
- **Android app:** Would need to read and render the snapshot format. A minimal
  read-only Android app or a simple web page reading a JSON export could work.
- **Best for:** Users who only need to check their list while shopping, never edit
  on mobile. A "shopping list export" (just grails + wantlist as a simple format)
  is a low-effort version of this.

---

**Option C — Shopping list export only (minimal, near-term)**

The simplest viable approach for the shopping use case: desktop exports a compact
JSON or CSV of the user's wantlist + grails (item name, line, franchise, notes,
any reference images). The user puts this file anywhere accessible on their phone
(Google Drive, cloud notes app, even just a text file).

- **No sync mechanism required.** User manually exports before going out.
- **No Android app required.** File is human-readable; or a simple static HTML
  file with embedded data could be generated for offline viewing in a browser.
- **Limitations:** No real-time, no marking as acquired in the field. But it covers
  the core need (checking what you want before buying) with zero infrastructure.
- **This should be implemented first** as a Phase 1–2 feature regardless of what
  mobile approach is chosen long-term, since it has immediate value and zero cost.

---

**Option D — PWA only, no native app**

A variant of Option A where the Android "app" is just the mobile-optimized web UI
served by the desktop, accessed via Tailscale. No app development required.
Progressive Web Apps can be "installed" on Android from Chrome (added to home
screen, runs full-screen). If the Tailscale connection is active, it works
identically to a native app for this use case.

- **Advantages:** One codebase, no app store, no Android SDK. Web UI can be built
  with any web framework (or plain HTML/CSS/JS).
- **Disadvantages:** Requires Tailscale to be running on the phone and the desktop
  to be on and running the server. No offline capability beyond what the browser
  caches.

---

**Recommended phased approach:**

| Phase | Feature | Effort |
|---|---|---|
| Near-term | Shopping list export (JSON + static HTML) | Low |
| Mid-term | Embedded FastAPI server + mobile-optimized PWA via Tailscale | Medium |
| Long-term | Native Android app with offline SQLite cache + sync | High |

The REST API surface designed for the PWA also serves as the foundation for a
future native Android app, so Option A and D are complementary — build A, get D
for free, and the native app (if ever built) just consumes the same API.

**What this is NOT:** A cloud service, a subscription, or a central database.
The desktop PC is the authoritative database. The phone is a client. Tailscale
is a routing layer, not a data store.

---

### Won't do (by design)

- Cloud sync or accounts — local-first is a core principle
- Selling/marketplace features — this is a catalog and tracker, not a store
- Real-time price feeds — snapshots on demand only, to respect API terms and
  avoid stale-data confusion
- A central server that holds user collection data (even optionally)

---

*End of research and design notes. Ready for implementation planning.*
