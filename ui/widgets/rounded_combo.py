"""Liste de sélection arrondie, y compris les coins de la fenêtre Windows."""
from core.i18n import tr
from ui.language import set_translated
from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtWidgets import QComboBox, QFrame, QListWidget, QListWidgetItem, QVBoxLayout


class ComboPopup(QFrame):
    def __init__(self, owner):
        super().__init__(owner, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.owner = owner
        self.setObjectName('RoundedPopup')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(2, 2, 2, 2)
        panel = QFrame()
        panel.setObjectName('ComboPopupPanel')
        inner = QVBoxLayout(panel)
        inner.setContentsMargins(8, 8, 8, 8)
        self.list = QListWidget()
        self.list.setObjectName('ComboPopupList')
        set_translated(self.list, 'setAccessibleName', tr('Sélection du tag'))
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setMouseTracking(True)
        self.list.itemClicked.connect(self._choose)
        self.list.itemActivated.connect(self._choose)
        inner.addWidget(self.list)
        outer.addWidget(panel)

    def populate(self):
        self.list.clear()
        for row in range(self.owner.count()):
            item = QListWidgetItem(self.owner.itemIcon(row), self.owner.itemText(row))
            item.setSizeHint(QSize(150, 40))
            set_translated(item, 'setToolTip', self.owner.itemText(row))
            self.list.addItem(item)
        self.list.setCurrentRow(self.owner.currentIndex())

    def _choose(self, item):
        row = self.list.row(item)
        if row < 0:
            return
        self.owner.hidePopup()
        self.owner.setCurrentIndex(row)
        self.owner.activated.emit(row)
        self.owner.setFocus(Qt.FocusReason.PopupFocusReason)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.owner.hidePopup()
            self.owner.setFocus(Qt.FocusReason.PopupFocusReason)
            event.accept()
        else:
            super().keyPressEvent(event)


class RoundedComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._popup = None

    def showPopup(self):
        if not self.count():
            return
        if self._popup is None:
            self._popup = ComboPopup(self)
        popup = self._popup
        popup.populate()
        popup.ensurePolished()
        popup.list.ensurePolished()
        available = self.screen().availableGeometry()
        width = min(max(self.width(), 220), available.width() - 16)
        height = min(sum(popup.list.sizeHintForRow(row) for row in range(self.count())) + 22,
                     342, available.height() - 16)
        below = self.mapToGlobal(QPoint(0, self.height() + 6))
        above = self.mapToGlobal(QPoint(0, -height - 6))
        x = max(available.left() + 8, min(below.x(), available.right() - width - 7))
        y = below.y() if below.y() + height <= available.bottom() - 8 else above.y()
        y = max(available.top() + 8, min(y, available.bottom() - height - 7))
        popup.resize(width, height)
        popup.move(x, y)
        popup.show()
        popup.list.setFocus(Qt.FocusReason.PopupFocusReason)
        popup.list.scrollToItem(popup.list.currentItem())

    def hidePopup(self):
        if self._popup:
            self._popup.hide()
        super().hidePopup()
