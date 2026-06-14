from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QVBoxLayout,
)

from figure_archive.plugins import loader


class LineDialog(QDialog):
    def __init__(self, parent=None, existing_name: str = "", show_type: bool = True):
        super().__init__(parent)
        self.setWindowTitle("Rename Line" if existing_name else "New Line")
        self.setMinimumWidth(360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._build_ui(existing_name, show_type)

    def _build_ui(self, existing_name: str, show_type: bool) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(10)

        self._name_edit = QLineEdit(existing_name)
        self._name_edit.setPlaceholderText("e.g. Generation 1")
        self._name_edit.textChanged.connect(self._on_text_changed)
        form.addRow(QLabel("Name:"), self._name_edit)

        self._type_combo = QComboBox()
        plugins = loader.list_type_plugins()
        if plugins:
            for plugin in plugins:
                self._type_combo.addItem(plugin.name, userData=plugin.id)
        else:
            # Fallback if plugins haven't been loaded (e.g. in tests)
            self._type_combo.addItem("Generic", userData="generic")
        # Default selection to Generic
        idx = self._type_combo.findData("generic")
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)
        if show_type:
            form.addRow(QLabel("Type:"), self._type_combo)

        layout.addLayout(form)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.button(QDialogButtonBox.Ok).setEnabled(bool(existing_name))
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._name_edit.selectAll()
        self._name_edit.setFocus()

    def _on_text_changed(self, text: str) -> None:
        self._buttons.button(QDialogButtonBox.Ok).setEnabled(bool(text.strip()))

    def name(self) -> str:
        return self._name_edit.text().strip()

    def type_plugin_id(self) -> str:
        return self._type_combo.currentData()
