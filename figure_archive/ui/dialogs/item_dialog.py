from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QInputDialog,
    QLabel, QLineEdit, QSpinBox, QVBoxLayout,
)

from figure_archive.db import waves as wave_db

ITEM_TYPES = ["figure", "vehicle", "playset", "accessory", "giftset", "other"]

_NEW_WAVE_SENTINEL = "__new_wave__"


class ItemDialog(QDialog):
    """Create a new item within a line. Allows picking or creating a wave."""

    def __init__(self, parent, line_id: str):
        super().__init__(parent)
        self._line_id = line_id
        self.setWindowTitle("Add Item")
        self.setMinimumWidth(380)
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

        self._type_combo = QComboBox()
        for t in ITEM_TYPES:
            self._type_combo.addItem(t.capitalize(), userData=t)
        form.addRow(QLabel("Type:"), self._type_combo)

        self._year_spin = QSpinBox()
        self._year_spin.setRange(0, 2100)
        self._year_spin.setSpecialValueText("—")
        self._year_spin.setValue(0)
        form.addRow(QLabel("Year:"), self._year_spin)

        self._wave_combo = QComboBox()
        self._reload_waves()
        self._wave_combo.currentIndexChanged.connect(self._on_wave_changed)
        form.addRow(QLabel("Wave:"), self._wave_combo)

        layout.addLayout(form)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.button(QDialogButtonBox.Ok).setText("Add")
        self._buttons.button(QDialogButtonBox.Ok).setEnabled(False)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._name_edit.setFocus()

    def _reload_waves(self, select_id: str | None = None) -> None:
        self._wave_combo.blockSignals(True)
        self._wave_combo.clear()
        self._wave_combo.addItem("No Wave", userData=None)
        for w in wave_db.list_waves(self._line_id):
            self._wave_combo.addItem(w["name"], userData=w["id"])
        self._wave_combo.addItem("＋ New Wave…", userData=_NEW_WAVE_SENTINEL)
        if select_id:
            idx = self._wave_combo.findData(select_id)
            if idx >= 0:
                self._wave_combo.setCurrentIndex(idx)
        self._wave_combo.blockSignals(False)

    def _on_wave_changed(self, _idx: int) -> None:
        if self._wave_combo.currentData() == _NEW_WAVE_SENTINEL:
            name, ok = QInputDialog.getText(self, "New Wave", "Wave name:")
            if ok and name.strip():
                wid = wave_db.create_wave(self._line_id, name.strip())
                self._reload_waves(select_id=wid)
            else:
                self._wave_combo.setCurrentIndex(0)  # back to No Wave

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
        data = self._wave_combo.currentData()
        return None if data in (None, _NEW_WAVE_SENTINEL) else data
