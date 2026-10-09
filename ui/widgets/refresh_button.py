from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen
from PySide6.QtWidgets import QPushButton

from ui.assets import refresh_icon_path


class RefreshButton(QPushButton):
    """Bouton actualiser avec icône custom et animation de rotation."""

    clicked_refresh = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RefreshBtn")
        self.setFixedSize(40, 40)
        self.setToolTip("Actualiser")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._rotation = 0.0
        self._icon = QIcon(str(refresh_icon_path()))
        self._animating = False

        self._animation = QPropertyAnimation(self, b"rotation")
        self._animation.setDuration(650)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(360.0)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.finished.connect(self._on_animation_finished)

        self.clicked.connect(self._on_click)

    def get_rotation(self) -> float:
        return self._rotation

    def set_rotation(self, value: float) -> None:
        self._rotation = value
        self.update()

    rotation = Property(float, get_rotation, set_rotation)

    def _on_click(self) -> None:
        if self._animating:
            return
        self._animating = True
        self.setEnabled(False)
        self._animation.stop()
        self._animation.setCurrentTime(0)
        self._animation.start()
        self.clicked_refresh.emit()

    def _on_animation_finished(self) -> None:
        self._rotation = 0.0
        self.update()
        self._animating = False
        self.setEnabled(True)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        bg = QColor("#26262C")
        border = QColor("#39393F")
        if self.underMouse() and self.isEnabled():
            bg = QColor("#303037")
            border = QColor("#4E4B59")

        painter.setBrush(bg)
        painter.setPen(QPen(border, 1))
        painter.drawRoundedRect(rect, 8, 8)

        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self._rotation)
        painter.translate(-self.width() / 2, -self.height() / 2)

        icon_size = 22
        x = (self.width() - icon_size) // 2
        y = (self.height() - icon_size) // 2
        self._icon.paint(painter, x, y, icon_size, icon_size)

        painter.end()
