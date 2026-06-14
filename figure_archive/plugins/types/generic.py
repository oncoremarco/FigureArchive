from .base import CollectionTypePlugin


class GenericTypePlugin(CollectionTypePlugin):
    id = "generic"
    name = "Generic"

    condition_vocabulary = ["Mint", "Near Mint", "Very Good", "Good", "Fair", "Poor"]
    packaging_states = ["Sealed", "Opened", "Loose"]
    has_accessory_list = False
    item_fields = []
    compatible_source_ids = []


PLUGIN = GenericTypePlugin
