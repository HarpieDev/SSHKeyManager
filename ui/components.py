"""Petits composants partagés par les écrans Harpie."""
from core.i18n import tr
from ui.language import set_translated, localized
from functools import lru_cache
from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

_PATHS = {
    "key": '<circle cx="7.5" cy="16.5" r="4.5"/><path d="m10.7 13.3 9-9m-3 3 3 3m-6 0 3 3"/>',
    "grid": '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
    "shield": '<path d="M12 3 4.5 6v6c0 4.8 7.5 9 7.5 9s7.5-4.2 7.5-9V6Z"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    "alert": '<path d="M10.3 4.9a2 2 0 0 1 3.4 0l7.2 12.5a2 2 0 0 1-1.7 3H4.8a2 2 0 0 1-1.7-3Z"/><path d="M12 9v4.5"/><circle cx="12" cy="16.5" r=".7" fill="currentColor" stroke="none"/>',
    "terminal": '<rect x="3" y="4.5" width="18" height="15" rx="3"/><path d="m7 9 3 3-3 3m6 0h4"/>',
    "trash": '<path d="M4 6h16M9 6V4h6v2M6 6l.7 13a2 2 0 0 0 2 2h6.6a2 2 0 0 0 2-2L18 6M10 10v7m4-7v7"/>',
    "folder": '<path d="M3 8V6a2 2 0 0 1 2-2h4l2 3h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
    "tag": '<path d="M4 4h6.5a2 2 0 0 1 1.4.6l8 8a2 2 0 0 1 0 2.8l-4.5 4.5a2 2 0 0 1-2.8 0l-8-8a2 2 0 0 1-.6-1.4Z"/><circle cx="8" cy="8" r="1"/>',
    "plus": '<path d="M12 5.5v13M5.5 12h13"/>',
    "import": '<path d="M12 3.5v11m-4-4 4 4 4-4M4.5 16v3a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-3"/>',
    "copy": '<rect x="8" y="8" width="12.5" height="12.5" rx="2.5"/><path d="M15.5 5.5v-1a2 2 0 0 0-2-2h-9a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h1"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5.5 5.5"/>',
    "refresh": '<path d="M19.5 8a8 8 0 1 0 .2 7.7M19.5 3v5h-5"/>',
    "arrow": '<path d="M5 12h14m-5-5 5 5-5 5"/>',
    "lock": '<rect x="5" y="10" width="14" height="11" rx="3"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
}


@lru_cache(maxsize=128)
def icon(name: str, color: str = "#AEAEB2", size: int = 20) -> QIcon:
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" color="{color}" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{_PATHS[name]}</svg>'
    # Double définition pour garder des traits nets sur les écrans Windows HiDPI.
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)


def label(text: str, role: str = "AppSubtitle") -> QLabel:
    widget = localized(QLabel(), text)
    widget.setObjectName(role)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    return widget


def button(text, callback, role="SecondaryBtn", symbol=None):
    widget = localized(QPushButton(), text)
    widget.setObjectName(role)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.setMinimumHeight(42)
    if symbol:
        widget.setIcon(icon(symbol, "#FFFFFF" if role == "PrimaryBtn" else "#EF89AD" if role in ("DangerBtn", "GhostDangerBtn") else "#59B4FF" if role == "TintedBtn" else "#AEAEB2"))
        widget.setIconSize(QSize(17, 17))
    widget.clicked.connect(callback)
    return widget


class SummaryCard(QFrame):
    """Un chiffre réel de la bibliothèque, indépendant des filtres de la liste."""

    def __init__(self, title: str, hint: str, symbol: str, tone: str, parent=None):
        super().__init__(parent)
        self.setObjectName("SummaryCard")
        self.setProperty("tone", tone)
        self.setMinimumHeight(112)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)
        top = QHBoxLayout()
        badge = QLabel()
        badge.setObjectName("SummaryIcon")
        badge.setFixedSize(36, 36)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        color = {"blue": "#81B3FF", "purple": "#AD93EB", "orange": "#F0B779"}.get(tone, "#FFFFFF")
        badge.setPixmap(icon(symbol, color, 20).pixmap(20, 20))
        self.value = label("0", "SummaryValue")
        self.value.setWordWrap(False)
        top.addWidget(self.value)
        top.addStretch()
        top.addWidget(badge)
        layout.addLayout(top)
        bottom = QHBoxLayout()
        bottom.addWidget(label(title, "SummaryTitle"))
        bottom.addStretch()
        caption = label(hint, "SummaryHint")
        self._hint = caption
        caption.setWordWrap(False)
        bottom.addWidget(caption)
        layout.addLayout(bottom)
        self._title = title
        self.set_count(0)

    def set_count(self, count: int) -> None:
        set_translated(self.value, 'setText', str(count))
        set_translated(self, 'setAccessibleName', f"{tr(self._title)} : {count}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._hint.setVisible(event.size().width() >= 300)


def field(title: str, control: QWidget) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(7)
    caption = label(title, "FieldLabel")
    caption.setBuddy(control)
    set_translated(control, 'setAccessibleName', title)
    layout.addWidget(caption)
    layout.addWidget(control)
    return widget


def key_type_name(value: str) -> str:
    return {"ssh-ed25519": "Ed25519", "ssh-rsa": "RSA", "ed25519": "Ed25519", "rsa": "RSA"}.get(value, value)


def dialog_header(title: str, subtitle: str, symbol: str = "key", tone: str = "blue") -> QWidget:
    """A consistent, accessible identity block for application dialogs."""
    header = QWidget()
    row = QHBoxLayout(header)
    row.setContentsMargins(0, 0, 0, 8)
    row.setSpacing(16)
    badge = QLabel()
    badge.setFixedSize(56, 56)
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    colors = {"blue": ("#1C304A", "#81B3FF"), "purple": ("#2D263F", "#AD93EB"), "pink": ("#34232D", "#E896B4")}
    background, foreground = colors[tone]
    badge.setStyleSheet(f"background: {background}; border-radius: 18px;")
    badge.setPixmap(icon(symbol, foreground, 26).pixmap(26, 26))
    row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
    text = QVBoxLayout()
    text.setSpacing(6)
    heading = label(title, "AppTitle")
    heading.setStyleSheet("font-size: 27px; font-weight: 600;")
    text.addWidget(heading)
    text.addWidget(label(subtitle))
    row.addLayout(text, 1)
    return header
