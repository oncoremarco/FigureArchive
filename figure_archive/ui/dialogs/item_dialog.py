from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QInputDialog, QLabel,
    QLineEdit, QVBoxLayout,
)

from figure_archive.db import waves as wave_db
from figure_archive.ui.widgets.no_scroll import NoScrollComboBox, NoScrollSpinBox

ITEM_TYPES = ["figure", "vehicle", "playset", "accessory", "giftset", "other"]

_NO_GROUP = "__no_group__"
_NEW_GROUP = "__new_group__"
_NEW_SUBGROUP = "__new_subgroup__"


class ItemDialog(QDialog):
    """Create a new item within a line."""

    def __init__(self, parent, line_id: str):
        super().__init__(parent)
        self._line_id = line_id
        self.setWindowTitle("Add Item")
        self.setMinimumWidth(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(10)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Optimus Prime")
        self._name_edit.textChanged.connect(self._on_text_changed)
        form.addRow(QLabel("Name:"), self._name_edit)

        self._type_combo = NoScrollComboBox()
        for t in ITEM_TYPES:
            self._type_combo.addItem(t.capitalize(), userData=t)
        form.addRow(QLabel("Type:"), self._type_combo)

        self._year_spin = NoScrollSpinBox()
        self._year_spin.setRange(0, 2100)
        self._year_spin.setSpecialValueText("—")
        self._year_spin.setValue(0)
        form.addRow(QLabel("Year:"), self._year_spin)

        self._group_combo = NoScrollComboBox()
        self._reload_groups()
        self._group_combo.currentIndexChanged.connect(self._on_group_changed)
        form.addRow(QLabel("Group:"), self._group_combo)

        layout.addLayout(form)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.button(QDialogButtonBox.Ok).setText("Add")
        self._buttons.button(QDialogButtonBox.Ok).setEnabled(False)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._name_edit.setFocus()

    def _reload_groups(self, select_id: str | None = None) -> None:
        self._group_combo.blockSignals(True)
        self._group_combo.clear()
        self._group_combo.addItem("No Group", userData=None)

        groups = wave_db.list_groups_tree(self._line_id)
        for g in groups:
            indent = "    " * g["depth"]  # nbsp indent
            label = f"{indent}{g['name']}" + (f"  {g['year']}" if g.get("year") else "")
            self._group_combo.addItem(label, userData=g["id"])

        self._group_combo.insertSeparator(self._group_combo.count())
        self._group_combo.addItem("＋ New Root Group…", userData=_NEW_GROUP)
        if groups:
            self._group_combo.addItem("＋ New Subgroup under…", userData=_NEW_SUBGROUP)

        if select_id:
            idx = self._group_combo.findData(select_id)
            if idx >= 0:
                self._group_combo.setCurrentIndex(idx)
        self._group_combo.blockSignals(False)

    def _on_group_changed(self, _idx: int) -> None:
        data = self._group_combo.currentData()
        if data == _NEW_GROUP:
            name, ok = QInputDialog.getText(self, "New Group", "Group name:")
            if ok and name.strip():
                gid = wave_db.create_wave(self._line_id, name.strip())
                self._reload_groups(select_id=gid)
            else:
                self._group_combo.setCurrentIndex(0)

        elif data == _NEW_SUBGROUP:
            groups = wave_db.list_groups_tree(self._line_id)
            if not groups:
                self._group_combo.setCurrentIndex(0)
                return
            # Ask user which parent
            parent_labels = []
            parent_ids = []
            for g in groups:
                indent = "    " * g["depth"]
                parent_labels.append(f"{indent}{g['name']}")
                parent_ids.append(g["id"])
            parent_label, ok = QInputDialog.getItem(
                self, "Choose Parent Group", "Create subgroup under:",
                parent_labels, editable=False,
            )
            if not ok:
                self._group_combo.setCurrentIndex(0)
                return
            parent_id = parent_ids[parent_labels.index(parent_label)]
            name, ok2 = QInputDialog.getText(self, "New Subgroup", "Subgroup name:")
            if ok2 and name.strip():
                gid = wave_db.create_wave(self._line_id, name.strip(), parent_id=parent_id)
                self._reload_groups(select_id=gid)
            else:
                self._group_combo.setCurrentIndex(0)

    def _on_text_changed(self, text: str) -> None:
        self._buttons.button(QDialogButtonBox.Ok).setEnabled(bool(text.strip()))

    # ── Results ──────────────────────────────────────────────────────────────

    def name(self) -> str:
        return self._name_edit.text().strip()

    def item_type(self) -> str:
        return self._type_combo.currentData()

    def year(self) -> int | None:
        v = self._year_spin.value()
        return v if v > 0 else None

    def wave_id(self) -> str | None:
        data = self._group_combo.currentData()
        return None if data in (None, _NO_GROUP, _NEW_GROUP, _NEW_SUBGROUP) else data
