import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from figure_archive.core import config
from figure_archive.db import connection as db_conn
from figure_archive.db.schema import apply_schema


def _load_stylesheet(app: QApplication) -> None:
    qss_path = Path(__file__).parent / "assets" / "styles" / "dark.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def _resolve_collection() -> Path | None:
    last = config.get("last_collection_path")
    if last and Path(last).exists():
        return Path(last)
    return None


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("FigureArchive")
    app.setOrganizationName("FigureArchive")

    _load_stylesheet(app)
    config.load()

    db_path = _resolve_collection()

    if db_path is None:
        from figure_archive.ui.dialogs.welcome_dialog import WelcomeDialog
        dlg = WelcomeDialog()
        _load_stylesheet(app)  # ensure dialog is styled
        if dlg.exec() != WelcomeDialog.Accepted or not dlg.db_path():
            sys.exit(0)
        db_path = dlg.db_path()

    conn = db_conn.open_collection(db_path)
    apply_schema(conn)
    config.set("last_collection_path", str(db_path))

    from figure_archive.ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())
