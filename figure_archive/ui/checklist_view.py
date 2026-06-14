from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QMenu, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)
from figure_archive.ui.widgets.thumbnail_loader import load_thumbnail_async

from figure_archive.db import items as item_db
from figure_archive.db import lines as line_db
from figure_archive.db import waves as wave_db
from figure_archive.db import collection_entries as ce
from figure_archive.db import franchises as franchise_db
from figure_archive.ui.dialogs.item_dialog import ItemDialog

# Ownership status → (label, color)
_STATUS = {
    ce.NOT_OWNED: ("", ""),
    ce.OWNED:     ("Owned", "#a6e3a1"),
    ce.SOLD:      ("Sold", "#6c7086"),
    ce.WANTED:    ("Wanted", "#89b4fa"),
    ce.ON_ORDER:  ("On Order", "#f9e2af"),
}

_TYPE_COLORS = {
    "figure": "#cba6f7", "vehicle": "#89dceb", "playset": "#f5c2e7",
    "accessory": "#94e2d5", "giftset": "#fab387", "other": "#6c7086",
}

# Indent per depth level in pixels
_INDENT_PX = 16


class ItemRow(QFrame):
    """A single checklist row."""
    clicked = Signal(str)             # item_id
    owned_toggled = Signal(str, int)  # item_id, new_status

    def __init__(self, item: dict, depth: int = 0):
        super().__init__()
        self._item = item
        self._item_id = item["id"]
        self._depth = depth
        self.setObjectName("itemRow")
        self.setStyleSheet(
            "#itemRow { border-radius: 6px; }"
            "#itemRow:hover { background-color: #2a2a3c; }"
        )
        self._build()

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        left_margin = 8 + self._depth * _INDENT_PX
        layout.setContentsMargins(left_margin, 6, 8, 6)
        layout.setSpacing(10)

        owned = self._item.get("owned") or 0
        self._check = QCheckBox()
        self._check.setChecked(owned == ce.OWNED)
        self._check.stateChanged.connect(self._on_check)
        layout.addWidget(self._check)

        thumb = QLabel()
        thumb.setFixedSize(40, 40)
        thumb.setStyleSheet(
            "background-color: #181825; border: 1px solid #313244;"
            "border-radius: 4px; color: #45475a;"
        )
        thumb.setAlignment(Qt.AlignCenter)
        primary = self._item.get("primary_image")
        if primary:
            load_thumbnail_async(thumb, primary, size=40)
        else:
            thumb.setText("▦")
        layout.addWidget(thumb)

        name = QLabel(self._item["name"])
        name.setStyleSheet("font-size: 13px;")
        layout.addWidget(name)

        if self._item.get("year"):
            year = QLabel(str(self._item["year"]))
            year.setStyleSheet("color: #6c7086; font-size: 11px;")
            layout.addWidget(year)

        layout.addStretch(1)

        # Type badge
        it = self._item.get("item_type", "figure")
        layout.addWidget(self._badge(it.capitalize(), _TYPE_COLORS.get(it, "#6c7086")))

        # Status badge
        label, color = _STATUS.get(owned, ("", ""))
        if label:
            layout.addWidget(self._badge(label, color))

        # Favorite star
        if self._item.get("is_favorite"):
            star = QLabel("★")
            star.setStyleSheet("color: #f9e2af; font-size: 14px;")
            layout.addWidget(star)

        # Needs-repair indicator
        if self._item.get("needs_repair"):
            wrench = QLabel("🔧")
            wrench.setToolTip("Needs repair")
            layout.addWidget(wrench)

    def _badge(self, text: str, color: str) -> QLabel:
        b = QLabel(text)
        b.setStyleSheet(
            f"color: {color}; border: 1px solid {color}; border-radius: 8px;"
            "padding: 1px 8px; font-size: 10px;"
        )
        return b

    def _on_check(self, state: int) -> None:
        new_status = ce.OWNED if state == Qt.Checked.value else ce.NOT_OWNED
        self.owned_toggled.emit(self._item_id, new_status)

    def mousePressEvent(self, event) -> None:
        if not self._check.underMouse():
            self.clicked.emit(self._item_id)
        super().mousePressEvent(event)


class GroupSeparator(QFrame):
    """Section header for a named group, indented by depth."""

    def __init__(self, name: str, total: int, owned: int,
                 year: int | None, depth: int = 0):
        super().__init__()
        layout = QHBoxLayout(self)
        left_margin = 8 + depth * _INDENT_PX
        layout.setContentsMargins(left_margin, 10 if depth == 0 else 6, 8, 4)

        title = name + (f"  {year}" if year else "")
        lbl = QLabel(title)
        # Root groups: bold blue; sub-groups: smaller, muted
        if depth == 0:
            lbl.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 12px;")
        else:
            lbl.setStyleSheet("font-weight: bold; color: #74c7ec; font-size: 11px;")
        layout.addWidget(lbl)

        if total:
            stats = QLabel(f"{total} · {owned} owned")
            stats.setStyleSheet("color: #6c7086; font-size: 10px;")
            layout.addWidget(stats)
        layout.addStretch(1)

        border_color = "#313244" if depth == 0 else "#1e1e2e"
        self.setStyleSheet(f"border-bottom: 1px solid {border_color};")


class ChecklistView(QWidget):
    item_selected = Signal(str)  # item_id
    data_changed = Signal()      # something changed; ask others to refresh

    def __init__(self):
        super().__init__()
        self._line_id: str | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet("background-color: #181825;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 12, 16, 12)
        self._title = QLabel("")
        self._title.setStyleSheet("font-size: 16px; font-weight: bold;")
        hl.addWidget(self._title)
        hl.addStretch(1)
        self._add_btn = QPushButton("＋ Add Item")
        self._add_btn.clicked.connect(self._add_item)
        hl.addWidget(self._add_btn)
        layout.addWidget(header)

        # Scrollable item list
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._container = QWidget()
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setContentsMargins(8, 8, 8, 8)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch(1)
        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll, 1)

    # ── Loading ──────────────────────────────────────────────────────────────

    def load_line(self, line_id: str) -> None:
        self._line_id = line_id
        line = next(
            (l for f in franchise_db.list_franchises()
             for l in line_db.list_lines(f["id"]) if l["id"] == line_id),
            None,
        )
        self._title.setText(line["name"] if line else "")
        self._rebuild()

    def refresh(self) -> None:
        if self._line_id:
            self._rebuild()

    def _clear_list(self) -> None:
        while self._list_layout.count() > 1:  # keep the trailing stretch
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _rebuild(self) -> None:
        self._clear_list()
        if not self._line_id:
            return

        all_items = item_db.list_items(self._line_id)
        # Depth-first flat list of groups with 'depth' key
        groups = wave_db.list_groups_tree(self._line_id)

        # Map group_id → items in that group (leaf attachment)
        by_group: dict[str | None, list[dict]] = {}
        for it in all_items:
            by_group.setdefault(it.get("wave_id"), []).append(it)

        insert_at = 0

        def _insert(widget) -> None:
            nonlocal insert_at
            self._list_layout.insertWidget(insert_at, widget)
            insert_at += 1

        def _add_items(group_items: list[dict], depth: int) -> None:
            for it in group_items:
                row = ItemRow(it, depth=depth)
                row.clicked.connect(self.item_selected)
                row.owned_toggled.connect(self._on_owned_toggled)
                _insert(row)

        def _count_owned(gid: str | None, groups_flat: list[dict]) -> tuple[int, int]:
            """Count total/owned items in this group and all its descendants."""
            gids = {gid}
            for g in groups_flat:
                if g.get("parent_id") in gids:
                    gids.add(g["id"])
            total = sum(len(by_group.get(g, [])) for g in gids)
            owned = sum(
                1 for g in gids
                for it in by_group.get(g, [])
                if (it.get("owned") or 0) == ce.OWNED
            )
            return total, owned

        # Unsorted items (no group) first
        if None in by_group:
            unsorted = by_group[None]
            sep = GroupSeparator(
                "Unsorted", len(unsorted),
                sum(1 for i in unsorted if (i.get("owned") or 0) == ce.OWNED),
                None, depth=0,
            )
            _insert(sep)
            _add_items(unsorted, depth=1)

        # Groups depth-first (list already ordered correctly by list_groups_tree)
        for g in groups:
            depth = g["depth"]
            group_items = by_group.get(g["id"], [])
            total, owned = _count_owned(g["id"], groups)
            # Only show header if the group or any descendant has items,
            # OR if the group itself exists (empty groups still show)
            sep = GroupSeparator(g["name"], total, owned, g.get("year"), depth=depth)
            _insert(sep)
            _add_items(group_items, depth=depth + 1)

        if not all_items:
            empty = QLabel('No items yet. Click "＋ Add Item" to start.')
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #45475a; padding: 40px;")
            self._list_layout.insertWidget(0, empty)

    # ── Slots ────────────────────────────────────────────────────────────────

    def _add_item(self) -> None:
        if not self._line_id:
            return
        dlg = ItemDialog(self, self._line_id)
        if dlg.exec() == ItemDialog.Accepted:
            item_db.create_item(
                self._line_id, dlg.name(), dlg.item_type(),
                wave_id=dlg.wave_id(), year=dlg.year(),
            )
            self._rebuild()
            self.data_changed.emit()

    def _on_owned_toggled(self, item_id: str, status: int) -> None:
        ce.set_owned(item_id, status)
        self._rebuild()
        self.data_changed.emit()
