from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
)

_PRESET = "#89b4fa"


class TagDialog(QDialog):
    """Create a new tag with a name and color."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Tag")
        self.setMinimumWidth(320)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._color = _PRESET
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(10)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. childhood")
        self._name_edit.textChanged.connect(self._on_text_changed)
        form.addRow(QLabel("Name:"), self._name_edit)

        color_row = QHBoxLayout()
        self._swatch = QLabel()
        self._swatch.setFixedSize(24, 24)
        self._update_swatch()
        pick = QPushButton("Pick Color…")
        pick.clicked.connect(self._pick_color)
        color_row.addWidget(self._swatch)
        color_row.addWidget(pick)
        color_row.addStretch(1)
        form.addRow(QLabel("Color:"), color_row)

        layout.addLayout(form)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.button(QDialogButtonBox.Ok).setEnabled(False)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._name_edit.setFocus()

    def _update_swatch(self) -> None:
        self._swatch.setStyleSheet(
            f"background-color: {self._color}; border-radius: 4px;"
            "border: 1px solid #45475a;"
        )

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self, "Tag color")
        if color.isValid():
            self._color = color.name()
            self._update_swatch()

    def _on_text_changed(self, text: str) -> None:
        self._buttons.button(QDialogButtonBox.Ok).setEnabled(bool(text.strip()))

    def name(self) -> str:
        return self._name_edit.text().strip()

    def color(self) -> str:
        return self._color
