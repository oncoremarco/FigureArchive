from figure_archive.plugins.sources.base import CatalogItem, SourcePlugin


class ManualSourcePlugin(SourcePlugin):
    """Fallback source for manually entered data — no external requests."""

    id = "manual"
    name = "Manual Entry"
    description = "No external source; all data entered by hand."

    supports_browse = False
    supports_search = False
    supports_url_import = False
    supports_upc_lookup = False
    supports_price_lookup = False

    compatible_type_ids = []  # works with any type


PLUGIN = ManualSourcePlugin
