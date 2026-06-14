from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel


class _Signals(QObject):
    done = Signal(QPixmap)


class _LoadTask(QRunnable):
    def __init__(self, path: str, size: int, signals: _Signals):
        super().__init__()
        self._path = path
        self._size = size
        self._signals = signals

    @Slot()
    def run(self) -> None:
        from figure_archive.core.image_cache import get_thumbnail_path
        try:
            thumb = get_thumbnail_path(self._path)
            if thumb and thumb.exists():
                from PySide6.QtCore import Qt
                px = QPixmap(str(thumb)).scaled(
                    self._size, self._size,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation,
                )
                self._signals.done.emit(px)
        except Exception:
            pass


def load_thumbnail_async(label: QLabel, local_path: str, size: int = 40) -> None:
    """Schedule async thumbnail load; updates label with pixmap when done."""
    sig = _Signals()
    sig.done.connect(lambda px, lbl=label: _apply(lbl, px))
    task = _LoadTask(local_path, size, sig)
    task.setAutoDelete(True)
    QThreadPool.globalInstance().start(task)


def _apply(label: QLabel, px: QPixmap) -> None:
    if not label or label.isHidden():
        return
    label.setText("")
    label.setPixmap(px)
