from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class StarRating(QWidget):
    """A clickable 1-5 star rating. 0 = unrated. Click the same star again to clear."""
    changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._stars: list[QLabel] = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        for i in range(1, 6):
            star = QLabel("☆")
            star.setStyleSheet("font-size: 18px; color: #6c7086;")
            star.setCursor(Qt.PointingHandCursor)
            star.mousePressEvent = lambda e, n=i: self._on_click(n)
            self._stars.append(star)
            layout.addWidget(star)
        layout.addStretch(1)

    def _on_click(self, n: int) -> None:
        self._value = 0 if self._value == n else n
        self._render()
        self.changed.emit(self._value)

    def set_value(self, value: int) -> None:
        self._value = value or 0
        self._render()

    def value(self) -> int:
        return self._value

    def _render(self) -> None:
        for i, star in enumerate(self._stars, start=1):
            if i <= self._value:
                star.setText("★")
                star.setStyleSheet("font-size: 18px; color: #f9e2af;")
            else:
                star.setText("☆")
                star.setStyleSheet("font-size: 18px; color: #6c7086;")
