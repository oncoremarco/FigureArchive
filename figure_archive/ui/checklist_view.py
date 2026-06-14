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


class ItemRow(QFrame):
    """A single checklist row."""
    clicked = Signal(str)             # item_id
    owned_toggled = Signal(str, int)  # item_id, new_status

    def __init__(self, item: dict):
        super().__init__()
        self._item = item
        self._item_id = item["id"]
        self.setObjectName("itemRow")
        self.setStyleSheet(
            "#itemRow { border-radius: 6px; }"
            "#itemRow:hover { background-color: #2a2a3c; }"
        )
        self._build()

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
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
        # Click anywhere except the checkbox opens detail
        if not self._check.underMouse():
            self.clicked.emit(self._item_id)
        super().mousePressEvent(event)


class WaveSeparator(QFrame):
    def __init__(self, name: str, total: int, owned: int, year: int | None):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 4)

        title = name + (f", {year}" if year else "")
        lbl = QLabel(title)
        lbl.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 12px;")
        layout.addWidget(lbl)

        stats = QLabel(f"{total} items · {owned} owned")
        stats.setStyleSheet("color: #6c7086; font-size: 11px;")
        layout.addWidget(stats)
        layout.addStretch(1)

        underline = QFrame()
        self.setStyleSheet("border-bottom: 1px solid #313244;")


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

        items = item_db.list_items(self._line_id)
        waves = wave_db.list_waves(self._line_id)

        # Group items by wave_id
        by_wave: dict[str | None, list[dict]] = {}
        for it in items:
            by_wave.setdefault(it["wave_id"], []).append(it)

        insert_at = 0

        def add_group(wave_name, wave_year, group):
            nonlocal insert_at
            if not group:
                return
            owned = sum(1 for g in group if (g.get("owned") or 0) == ce.OWNED)
            sep = WaveSeparator(wave_name, len(group), owned, wave_year)
            self._list_layout.insertWidget(insert_at, sep)
            insert_at += 1
            for it in group:
                row = ItemRow(it)
                row.clicked.connect(self.item_selected)
                row.owned_toggled.connect(self._on_owned_toggled)
                self._list_layout.insertWidget(insert_at, row)
                insert_at += 1

        # Items with no wave first
        if None in by_wave:
            add_group("Unsorted", None, by_wave[None])
        # Then each defined wave in order
        for w in waves:
            add_group(w["name"], w.get("year"), by_wave.get(w["id"], []))

        if not items:
            empty = QLabel('No items yet. Click "Add Item" to start.')
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
