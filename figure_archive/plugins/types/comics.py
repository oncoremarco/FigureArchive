from .base import CollectionTypePlugin, FieldDefinition


class ComicsTypePlugin(CollectionTypePlugin):
    id = "comics"
    name = "Comics"

    # CGC-style numeric grades plus simplified descriptors.
    condition_vocabulary = [
        "10.0 (Gem Mint)", "9.8", "9.6", "9.4", "9.2", "9.0",
        "8.5", "8.0", "7.0", "6.0", "5.0", "4.0", "3.0", "2.0", "1.0",
        "Mint", "Near Mint", "Very Fine", "Fine", "Good", "Poor",
    ]
    packaging_states = ["Slabbed (Graded)", "Bagged & Boarded", "Raw"]
    has_accessory_list = False

    item_fields = [
        FieldDefinition("issue_number", "Issue #", "text"),
        FieldDefinition("upc", "UPC", "text"),
        FieldDefinition("writer", "Writer", "text"),
        FieldDefinition("artist", "Artist", "text"),
    ]

    compatible_source_ids = ["metron", "comicvine", "ebay_auction", "manual"]


PLUGIN = ComicsTypePlugin
