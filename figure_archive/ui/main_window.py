from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QLabel, QMainWindow, QSplitter,
    QStackedWidget, QStatusBar, QWidget, QVBoxLayout,
)

from figure_archive.core import config
from figure_archive.db import connection as db_conn
from figure_archive.db.schema import apply_schema
from figure_archive.ui.sidebar import Sidebar
from figure_archive.ui.checklist_view import ChecklistView
from figure_archive.ui.detail_panel import DetailPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FigureArchive")
        self.setMinimumSize(900, 600)
        self.resize(1280, 800)
        self._build_ui()
        self._build_menu()
        self._update_status()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setHandleWidth(1)

        # Sidebar
        self._sidebar = Sidebar()
        self._sidebar.setMinimumWidth(180)
        self._sidebar.line_selected.connect(self._on_line_selected)
        self._splitter.addWidget(self._sidebar)

        # Center: stacked (placeholder or checklist)
        self._center = QStackedWidget()
        placeholder = QLabel("Select a line to begin")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #45475a; font-size: 15px;")
        self._center.addWidget(placeholder)

        self._checklist = ChecklistView()
        self._checklist.item_selected.connect(self._on_item_selected)
        self._checklist.data_changed.connect(self._on_data_changed)
        self._center.addWidget(self._checklist)
        self._splitter.addWidget(self._center)

        # Detail panel (hidden until an item is selected)
        self._detail = DetailPanel()
        self._detail.closed.connect(self._hide_detail)
        self._detail.data_saved.connect(self._checklist.refresh)
        self._detail.hide()
        self._splitter.addWidget(self._detail)

        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 0)
        self._splitter.setSizes([240, 700, 360])

        self.setCentralWidget(self._splitter)
        self.setStatusBar(QStatusBar())

    def _build_menu(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Collection…", self._new_collection)
        file_menu.addAction("Open Collection…", self._open_collection)
        file_menu.addSeparator()
        file_menu.addAction("Quit", self.close)

    # ── Status bar ───────────────────────────────────────────────────────────

    def _update_status(self) -> None:
        path = db_conn.current_path()
        if path:
            self.statusBar().showMessage(f"Collection: {path.parent.name}  ·  {path}")

    # ── Slots ────────────────────────────────────────────────────────────────

    def _on_line_selected(self, line_id: str) -> None:
        self._checklist.load_line(line_id)
        self._center.setCurrentWidget(self._checklist)
        self._hide_detail()

    def _on_item_selected(self, item_id: str) -> None:
        self._detail.load_item(item_id)
        self._detail.show()

    def _hide_detail(self) -> None:
        self._detail.hide()

    def _on_data_changed(self) -> None:
        # ownership toggled in checklist; nothing else to refresh for now
        pass

    def _new_collection(self) -> None:
        from figure_archive.ui.dialogs.welcome_dialog import WelcomeDialog
        dlg = WelcomeDialog(self)
        if dlg.exec() == WelcomeDialog.Accepted and dlg.db_path():
            self._switch_collection(dlg.db_path())

    def _open_collection(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Collection",
            str(config.collections_dir()),
            "Collection files (*.db);;All files (*)",
        )
        if path:
            self._switch_collection(Path(path))

    def _switch_collection(self, path: Path) -> None:
        db_conn.close_collection()
        conn = db_conn.open_collection(path)
        apply_schema(conn)
        config.set("last_collection_path", str(path))
        self._sidebar.load_tree()
        self._center.setCurrentIndex(0)
        self._hide_detail()
        self._update_status()
