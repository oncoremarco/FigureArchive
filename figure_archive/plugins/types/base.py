from dataclasses import dataclass, field


@dataclass
class FieldDefinition:
    """Describes one type-specific catalog field for an item."""
    id: str
    label: str
    field_type: str = "text"   # text, integer, float, boolean, dropdown, date
    options: list[str] = field(default_factory=list)  # for dropdown
    required: bool = False
    default: object = None


class CollectionTypePlugin:
    """Base class for collection type plugins.

    A type plugin defines the vocabulary and field schema for a category of
    collectible (action figures, comics, vinyl, etc.). The app core stays
    generic; type plugins supply the domain-specific pieces.
    """

    id: str = "base"
    name: str = "Base"

    # Condition grade vocabulary shown in the detail panel.
    condition_vocabulary: list[str] = []

    # Packaging / sealing states (MOC, MIB, Loose ...). Empty = not applicable.
    packaging_states: list[str] = []

    # Whether items of this type track an accessory checklist.
    has_accessory_list: bool = False

    # Extra catalog fields beyond the universal item fields.
    item_fields: list[FieldDefinition] = []

    # Source plugin ids this type can import from ([] = any).
    compatible_source_ids: list[str] = []
