from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QLabel, QMainWindow, QSplitter,
    QStackedWidget, QStatusBar,
)

from figure_archive.core import config
from figure_archive.db import connection as db_conn
from figure_archive.db.schema import apply_schema
from figure_archive.ui.sidebar import Sidebar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FigureArchive")
        self.setMinimumSize(900, 600)
        self.resize(1200, 750)
        self._build_ui()
        self._build_menu()
        self._update_status()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        self._sidebar = Sidebar()
        self._sidebar.setMinimumWidth(180)
        self._sidebar.line_selected.connect(self._on_line_selected)
        splitter.addWidget(self._sidebar)

        self._content = QStackedWidget()
        placeholder = QLabel("Select a line to begin")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #45475a; font-size: 15px;")
        self._content.addWidget(placeholder)
        splitter.addWidget(self._content)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([240, 960])

        self.setCentralWidget(splitter)
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
            self.statusBar().showMessage(
                f"Collection: {path.parent.name}  ·  {path}"
            )

    # ── Slots ────────────────────────────────────────────────────────────────

    def _on_line_selected(self, line_id: str) -> None:
        # Phase 2 will replace this placeholder
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
        self._update_status()
