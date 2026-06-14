from .base import CollectionTypePlugin, FieldDefinition


class ActionFiguresTypePlugin(CollectionTypePlugin):
    id = "action_figures"
    name = "Action Figures"

    # C-scale (collector standard) plus simplified descriptors.
    condition_vocabulary = [
        "C-10 (Mint)", "C-9.5", "C-9", "C-8", "C-7", "C-6",
        "C-5", "C-4", "C-3", "C-2", "C-1 (Poor)",
        "Mint", "Near Mint", "Very Good", "Good", "Poor",
    ]
    packaging_states = [
        "MOC", "MIB", "MISB", "Loose", "Complete", "Incomplete", "Parts Only",
    ]
    has_accessory_list = True

    item_fields = [
        FieldDefinition("scale", "Scale", "text"),
        FieldDefinition("upc", "UPC", "text"),
        FieldDefinition("accessories", "Accessories", "text"),
    ]

    compatible_source_ids = [
        "figurerealm", "figure_archive", "theafdb", "transformerland",
        "ebay_auction", "manual",
    ]


PLUGIN = ActionFiguresTypePlugin
