from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from ui.theme import chip_colors, BORDER, HOVER, PANEL, SECONDARY, SELECTED
from ui.appearance import smooth_text_font


class TagDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.column() != 0:
            super().paint(painter, option, index)
            return

        key = index.data(Qt.ItemDataRole.UserRole)
        if not key:
            super().paint(painter, option, index)
            return

        label = getattr(key, "tag_label", "")
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        base_font = QFont(option.font)
        smooth_text_font(base_font)
        painter.setFont(base_font)
        selected = option.state & QStyle.StateFlag.State_Selected
        hovered = option.state & QStyle.StateFlag.State_MouseOver
        painter.fillRect(option.rect, QColor(SELECTED if selected else HOVER if hovered else PANEL))
        painter.setPen(QPen(QColor(BORDER)))
        painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
        painter.restore()
        if not label:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            painter.setFont(base_font)
            painter.setPen(QColor(SECONDARY))
            painter.drawText(option.rect.adjusted(8, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, "—")
            painter.restore()
            return

        color = getattr(key, "tag_color", "#64748B")
        bg, fg, border = chip_colors(color)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        font = QFont(option.font)
        smooth_text_font(font)
        font.setPixelSize(12)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)

        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(label)
        chip_w = min(text_width + 24, option.rect.width() - 8)
        chip_h = 24
        x = option.rect.x() + 8
        y = option.rect.y() + (option.rect.height() - chip_h) // 2
        chip_rect = QRect(x, y, chip_w, chip_h)

        painter.setBrush(QColor(bg))
        painter.setPen(QPen(QColor(border), 1))
        painter.drawRoundedRect(chip_rect, 12, 12)

        painter.setPen(QColor(fg))
        text = metrics.elidedText(label, Qt.TextElideMode.ElideRight, max(0, chip_w - 20))
        painter.drawText(chip_rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        if index.column() == 0:
            return QSize(120, 40)
        return super().sizeHint(option, index)
