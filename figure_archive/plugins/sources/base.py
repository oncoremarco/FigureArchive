from dataclasses import dataclass, field


@dataclass
class CatalogItem:
    """Minimal catalog record returned by source plugins."""
    source_id: str
    external_id: str
    name: str
    item_type: str = "figure"
    year: int | None = None
    manufacturer: str | None = None
    scale: str | None = None
    upc: str | None = None
    description: str | None = None
    image_urls: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


class SourcePlugin:
    """Base class for catalog/data source plugins."""

    id: str = "base"
    name: str = "Base Source"
    base_url: str = ""
    description: str = ""

    supports_browse: bool = False
    supports_search: bool = False
    supports_url_import: bool = False
    supports_upc_lookup: bool = False
    supports_price_lookup: bool = False

    rate_limit_seconds: float = 1.0
    compatible_type_ids: list[str] = []

    # ── Browse ────────────────────────────────────────────────────────────────

    def get_franchises(self) -> list[dict]:
        """Return list of {id, name} dicts from the source."""
        return []

    def get_lines(self, franchise_id: str) -> list[dict]:
        """Return list of {id, name} dicts for the given franchise."""
        return []

    def get_waves(self, line_id: str) -> list[dict]:
        """Return list of {id, name, year} dicts for the given line."""
        return []

    def get_items(self, line_id: str) -> list[CatalogItem]:
        """Return all items for the given line."""
        return []

    # ── Detail ────────────────────────────────────────────────────────────────

    def get_item_detail(self, external_id: str) -> CatalogItem | None:
        """Return full detail for a single item by external ID."""
        return None

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, query: str, **kwargs) -> list[CatalogItem]:
        """Full-text search across the source."""
        return []

    # ── URL / UPC import ─────────────────────────────────────────────────────

    def import_from_url(self, url: str) -> CatalogItem | None:
        """Parse a URL and return a CatalogItem, or None if unsupported."""
        return None

    def lookup_upc(self, upc: str) -> CatalogItem | None:
        """Look up an item by UPC barcode."""
        return None

    # ── Price ─────────────────────────────────────────────────────────────────

    def get_price(self, external_id: str, condition: str | None = None) -> float | None:
        """Return estimated market price, or None if unavailable."""
        return None
