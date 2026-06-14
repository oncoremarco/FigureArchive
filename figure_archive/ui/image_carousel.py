from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMenu, QPushButton, QScrollArea,
    QSizePolicy, QWidget,
)

from figure_archive.core import image_cache

_THUMB_PX = 72
_ACCEPT = "Images (*.jpg *.jpeg *.png *.gif *.webp);;All files (*)"


class _ThumbButton(QPushButton):
    """Square thumbnail with right-click → Remove."""
    remove_requested = Signal(str)  # local_path

    def __init__(self, local_path: str):
        super().__init__()
        self._path = local_path
        self.setFixedSize(_THUMB_PX, _THUMB_PX)
        self.setStyleSheet(
            "border: 2px solid #313244; border-radius: 4px;"
            "background-color: #181825;"
        )
        self._load_pixmap()

    def _load_pixmap(self) -> None:
        thumb = image_cache.get_thumbnail_path(self._path)
        if thumb and thumb.exists():
            px = QPixmap(str(thumb)).scaled(
                _THUMB_PX, _THUMB_PX, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation,
            )
            self.setIcon(px)
            from PySide6.QtCore import QSize
            self.setIconSize(QSize(_THUMB_PX, _THUMB_PX))
        else:
            self.setText("▦")

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.addAction("Remove", lambda: self.remove_requested.emit(self._path))
        menu.exec(event.globalPos())


class ImageCarousel(QWidget):
    """Horizontal strip of image thumbnails with optional Add button."""
    image_selected = Signal(str)   # clicked local_path
    image_added = Signal(str)      # new local_path after file pick
    image_removed = Signal(str)    # removed local_path

    def __init__(self, can_add: bool = True, parent=None):
        super().__init__(parent)
        self._can_add = can_add
        self._paths: list[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setFixedHeight(_THUMB_PX + 8)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(scroll.Shape.NoFrame)

        self._inner = QWidget()
        self._row = QHBoxLayout(self._inner)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(6)
        self._row.addStretch(1)

        scroll.setWidget(self._inner)
        outer.addWidget(scroll, 1)

    def set_images(self, paths: list[str]) -> None:
        self._paths = list(paths)
        self._rebuild()

    def _rebuild(self) -> None:
        while self._row.count():
            item = self._row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for p in self._paths:
            btn = _ThumbButton(p)
            btn.clicked.connect(lambda _=False, path=p: self.image_selected.emit(path))
            btn.remove_requested.connect(self._on_remove)
            self._row.addWidget(btn)

        if self._can_add:
            add_btn = QPushButton("＋")
            add_btn.setFixedSize(_THUMB_PX, _THUMB_PX)
            add_btn.setStyleSheet(
                "border: 2px dashed #45475a; border-radius: 4px;"
                "color: #6c7086; font-size: 20px;"
                "background-color: transparent;"
            )
            add_btn.clicked.connect(self._pick_file)
            self._row.addWidget(add_btn)

        self._row.addStretch(1)

    def _pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select image", "", _ACCEPT)
        if path:
            self.image_added.emit(path)

    def _on_remove(self, path: str) -> None:
        self.image_removed.emit(path)
