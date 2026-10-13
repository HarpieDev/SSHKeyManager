from core.i18n import tr
from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from ui.components import icon
from ui.appearance import smooth_text_font
from ui.theme import ACCENT, BORDER, HOVER, PANEL, SECONDARY, SELECTED, TEXT, WARNING


class KeyDelegate(QStyledItemDelegate):
    """Nom et commentaire sur deux lignes, avec une identité visuelle stable."""

    def paint(self, painter, option, index):
        key = index.data(Qt.ItemDataRole.UserRole)
        if not key:
            return
        painter.save()
        selected = option.state & QStyle.StateFlag.State_Selected
        hovered = option.state & QStyle.StateFlag.State_MouseOver
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.fillRect(option.rect, QColor(SELECTED if selected else HOVER if hovered else PANEL))
        painter.setPen(QPen(QColor(BORDER)))
        painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
        x, y = option.rect.x(), option.rect.y()
        symbol = QRect(x + 8, y + (option.rect.height() - 36) // 2, 36, 36)
        painter.setPen(Qt.PenStyle.NoPen)
        rsa = key.key_type in ("rsa", "ssh-rsa")
        painter.setBrush(QColor("#372B22" if key.warning else "#2D263F" if rsa else "#1C304A"))
        painter.drawRoundedRect(symbol, 12, 12)
        icon("key", WARNING if key.warning else "#AD93EB" if rsa else ACCENT).paint(painter, symbol.adjusted(8, 8, -8, -8))
        font = QFont(option.font)
        smooth_text_font(font)
        font.setPixelSize(14)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(QColor(WARNING if key.warning else TEXT))
        rect = option.rect.adjusted(56, 15, -12, -36)
        painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(key.name, Qt.TextElideMode.ElideRight, rect.width()))
        font.setPixelSize(12)
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor(SECONDARY))
        rect = option.rect.adjusted(56, 40, -12, -12)
        text = key.comment or (tr('Clé publique seule') if not key.has_private else tr('Clé SSH personnelle'))
        painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, rect.width()))
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(240, 76)
