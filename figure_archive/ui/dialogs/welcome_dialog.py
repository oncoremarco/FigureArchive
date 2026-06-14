from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from figure_archive.core import config


class WelcomeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to FigureArchive")
        self.setMinimumWidth(520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._db_path: Path | None = None
        self._build_ui()

    # ── UI construction ─────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(20)
        root.setContentsMargins(32, 32, 32, 24)

        # Header
        title = QLabel("FigureArchive")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #89b4fa;")
        subtitle = QLabel("A local-first collection tracker for action figures and more.")
        subtitle.setStyleSheet("color: #6c7086; font-size: 12px;")
        root.addWidget(title)
        root.addWidget(subtitle)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #313244;")
        root.addWidget(line)

        # Create new section
        root.addWidget(self._section_label("Create a new collection"))
        root.addWidget(self._create_panel())

        # Divider
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("color: #313244;")
        root.addWidget(line2)

        # Open existing section
        root.addWidget(self._section_label("Open an existing collection"))
        root.addWidget(self._open_panel())

        # Buttons
        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.button(QDialogButtonBox.Ok).setText("Open")
        self._buttons.button(QDialogButtonBox.Ok).setEnabled(False)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        root.addWidget(self._buttons)

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: bold; color: #a6adc8; font-size: 12px;")
        return lbl

    def _create_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Collection name
        name_row = QHBoxLayout()
        name_lbl = QLabel("Name:")
        name_lbl.setFixedWidth(60)
        self._name_edit = QLineEdit("My Collection")
        self._name_edit.textChanged.connect(self._on_name_changed)
        name_row.addWidget(name_lbl)
        name_row.addWidget(self._name_edit)
        layout.addLayout(name_row)

        # Folder path
        folder_row = QHBoxLayout()
        folder_lbl = QLabel("Folder:")
        folder_lbl.setFixedWidth(60)
        self._folder_edit = QLineEdit()
        self._folder_edit.setReadOnly(True)
        self._folder_edit.setStyleSheet("color: #6c7086;")
        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_new_folder)
        folder_row.addWidget(folder_lbl)
        folder_row.addWidget(self._folder_edit)
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        # Initialise path from default
        self._on_name_changed(self._name_edit.text())
        return panel

    def _open_panel(self) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        self._open_path_label = QLabel("No file selected")
        self._open_path_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        open_btn = QPushButton("Browse for .db file…")
        open_btn.clicked.connect(self._browse_existing)
        layout.addWidget(open_btn)
        layout.addWidget(self._open_path_label, 1)
        return panel

    # ── Slots ───────────────────────────────────────────────────────────────

    def _on_name_changed(self, text: str) -> None:
        safe = text.strip()
        if safe:
            default_path = config.collections_dir() / safe / "collection.db"
            self._folder_edit.setText(str(default_path))
            self._db_path = default_path
            if hasattr(self, "_buttons"):
                self._buttons.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self._folder_edit.setText("")
            if not self._open_path_label.text().endswith(".db"):
                self._db_path = None
                if hasattr(self, "_buttons"):
                    self._buttons.button(QDialogButtonBox.Ok).setEnabled(False)

    def _browse_new_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Choose folder for new collection",
            str(config.collections_dir()),
        )
        if folder:
            name = self._name_edit.text().strip() or "collection"
            self._db_path = Path(folder) / f"{name}.db"
            self._folder_edit.setText(str(self._db_path))
            self._buttons.button(QDialogButtonBox.Ok).setEnabled(True)

    def _browse_existing(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open collection",
            str(config.collections_dir()),
            "Collection files (*.db);;All files (*)",
        )
        if path:
            self._db_path = Path(path)
            self._open_path_label.setText(path)
            self._open_path_label.setStyleSheet("color: #cdd6f4; font-size: 11px;")
            self._buttons.button(QDialogButtonBox.Ok).setEnabled(True)

    # ── Result ───────────────────────────────────────────────────────────────

    def db_path(self) -> Path | None:
        return self._db_path
