"""Gestion des tags dans l'application, sans boîte de sélection native."""
from core.i18n import tr
from ui.language import set_translated
import re
from collections import Counter

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QScrollArea, QSizePolicy, QStackedWidget, QStyle,
    QStyledItemDelegate, QVBoxLayout, QWidget,
)

from core import metadata_store
from ui.appearance import smooth_text_font
from ui.components import button, field, icon, label
from ui.theme import COLOR_PALETTE, HOVER, PANEL, SECONDARY, SELECTED, TEXT, chip_colors
from ui.widgets.tags import ColorPalettePicker


class TagListDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        tag = index.data(Qt.ItemDataRole.UserRole)
        if not tag:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.fillRect(option.rect, QColor(PANEL))
        rect = option.rect.adjusted(2, 3, -2, -3)
        selected = option.state & QStyle.StateFlag.State_Selected
        hovered = option.state & QStyle.StateFlag.State_MouseOver
        painter.setPen(Qt.PenStyle.NoPen)
        if selected or hovered:
            painter.setBrush(QColor(SELECTED if selected else HOVER))
            painter.drawRoundedRect(rect, 16, 16)
        bg, fg, _ = chip_colors(tag['color'])
        badge = rect.adjusted(12, 0, 0, 0)
        badge.setTop(rect.center().y() - 17)
        badge.setSize(QSize(34, 34))
        painter.setBrush(QColor(bg))
        painter.drawEllipse(badge)
        icon('tag', fg, 18).paint(painter, badge.adjusted(8, 8, -8, -8))
        font = QFont(option.font)
        smooth_text_font(font)
        font.setPixelSize(15)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(QColor(TEXT))
        name_rect = rect.adjusted(58, 10, -14, -30)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(tag['label'], Qt.TextElideMode.ElideRight, name_rect.width()))
        font.setPixelSize(12)
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor(SECONDARY))
        count = tag.get('count', 0)
        painter.drawText(rect.adjusted(58, 34, -14, -8), Qt.AlignmentFlag.AlignVCenter,
                         tr('{p0} clé{p1}', p0=count, p1='s' if count != 1 else ''))
        if option.state & QStyle.StateFlag.State_HasFocus:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor('#2197FE'), 1))
            painter.drawRoundedRect(rect, 16, 16)
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(180, 68)


class TagPreview(QLabel):
    def __init__(self):
        super().__init__()
        self._full_text = ''
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setMinimumWidth(0)
        self.setFixedHeight(42)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

    def set_tag(self, text, color):
        self._full_text = text
        bg, fg, border = chip_colors(color)
        self.setStyleSheet(f'background: {bg}; color: {fg}; border: 1px solid {border}; '
                          'border-radius: 18px; padding: 0 14px; font-size: 14px; font-weight: 500;')
        set_translated(self, 'setToolTip', text)
        set_translated(self, 'setAccessibleName', tr('Aperçu du tag : {p0}', p0=text))
        self._elide()

    def _elide(self):
        set_translated(self, 'setText', self.fontMetrics().elidedText(self._full_text, Qt.TextElideMode.ElideRight,
                                                 max(0, self.width() - 30)))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._elide()


class TagPage(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._editing_id = None
        self._original = ('', COLOR_PALETTE[12])
        self._counts = Counter()
        self._tags = []
        self._loading = False
        self._pending_action = None
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 18)
        root.setSpacing(18)
        root.addWidget(label(tr('ESPACE PERSONNEL  /  ORGANISATION'), 'Eyebrow'))
        heading = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(5)
        titles.addWidget(label(tr('Une place pour chaque clé.'), 'AppTitle'))
        titles.addWidget(label(tr('Organisez vos clés par projet ou par usage.')))
        heading.addLayout(titles, 1)
        heading.addWidget(button(tr('Nouveau tag'), self._request_new, 'PrimaryBtn', 'plus'))
        root.addLayout(heading)
        body = QHBoxLayout()
        body.setSpacing(18)
        left = QFrame()
        left.setObjectName('Card')
        collection = QVBoxLayout(left)
        collection.setContentsMargins(14, 20, 14, 14)
        collection.setSpacing(12)
        self._count_label = label(tr('Mes tags'), 'SectionTitle')
        self._count_label.setContentsMargins(8, 0, 8, 0)
        collection.addWidget(self._count_label)
        self._search = QLineEdit()
        self._search.setObjectName('SearchField')
        set_translated(self._search, 'setPlaceholderText', tr('Rechercher un tag'))
        self._search.setClearButtonEnabled(True)
        self._search.addAction(icon('search'), QLineEdit.ActionPosition.LeadingPosition)
        self._search.textChanged.connect(self._filter)
        collection.addWidget(self._search)
        self._list = QListWidget()
        self._list.setObjectName('TagList')
        self._list.setItemDelegate(TagListDelegate(self._list))
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setMouseTracking(True)
        set_translated(self._list, 'setAccessibleName', tr('Liste des tags'))
        self._list.currentItemChanged.connect(self._selection_changed)
        self._list_stack = QStackedWidget()
        self._list_stack.addWidget(self._list)
        self._empty = label(tr('Aucun tag\nCréez votre premier tag pour organiser vos clés.'))
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setContentsMargins(18, 20, 18, 20)
        self._list_stack.addWidget(self._empty)
        collection.addWidget(self._list_stack, 1)
        body.addWidget(left, 3)
        right = QFrame()
        right.setObjectName('Card')
        editor = QVBoxLayout(right)
        editor.setContentsMargins(0, 0, 0, 0)
        editor.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_container = QWidget()
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setContentsMargins(0, 10, 10, 0)
        scroll_layout.addWidget(scroll)
        page = QWidget()
        form = QVBoxLayout(page)
        form.setContentsMargins(24, 14, 14, 16)
        form.setSpacing(16)
        self._editor_title = label(tr('Créer un tag'), 'SectionTitle')
        form.addWidget(self._editor_title)
        self._usage = label(tr('Choisissez un nom et une couleur.'))
        form.addWidget(self._usage)
        self._name = QLineEdit()
        set_translated(self._name, 'setPlaceholderText', tr('ex. Production, Personnel, CTOS…'))
        set_translated(self._name, 'setAccessibleName', tr('Nom du tag'))
        self._name.textChanged.connect(self._update_form)
        form.addWidget(field(tr('Nom du tag'), self._name))
        color_header = QHBoxLayout()
        color_header.addWidget(label(tr('Couleur'), 'FieldLabel'))
        color_header.addStretch()
        self._hex = QLineEdit(COLOR_PALETTE[12])
        self._hex.setFixedWidth(108)
        self._hex.setMaxLength(7)
        set_translated(self._hex, 'setAccessibleName', tr('Couleur du tag au format hexadécimal'))
        self._hex.textChanged.connect(self._hex_changed)
        color_header.addWidget(self._hex)
        form.addLayout(color_header)
        self._palette = ColorPalettePicker()
        self._palette.color_changed.connect(self._color_changed)
        form.addWidget(self._palette)
        form.addWidget(label(tr('Aperçu dans la liste des clés'), 'FieldLabel'))
        self._preview = TagPreview()
        form.addWidget(self._preview)
        form.addStretch()
        scroll.setWidget(page)
        editor.addWidget(scroll_container, 1)
        footer = QVBoxLayout()
        footer.setContentsMargins(24, 12, 24, 24)
        footer.setSpacing(10)
        self._feedback = label('', 'TagError')
        self._feedback.hide()
        footer.addWidget(self._feedback)
        self._save_btn = button(tr('Créer le tag'), self._save, 'PrimaryBtn')
        footer.addWidget(self._save_btn)
        self._delete_btn = button(tr('Supprimer ce tag'), self._request_delete, 'GhostDangerBtn', 'trash')
        footer.addWidget(self._delete_btn)
        self._notice = QFrame()
        self._notice.setObjectName('TagNotice')
        notice = QVBoxLayout(self._notice)
        notice.setContentsMargins(16, 16, 16, 16)
        notice.setSpacing(10)
        self._notice_title = label('', 'FieldLabel')
        self._notice_text = label('')
        notice.addWidget(self._notice_title)
        notice.addWidget(self._notice_text)
        actions = QHBoxLayout()
        actions.addWidget(button(tr('Annuler'), self._cancel_notice))
        self._confirm_btn = button(tr('Confirmer'), self._confirm_notice, 'DangerBtn')
        actions.addWidget(self._confirm_btn)
        notice.addLayout(actions)
        footer.addWidget(self._notice)
        self._notice.hide()
        editor.addLayout(footer)
        body.addWidget(right, 4)
        root.addLayout(body, 1)
        root.addWidget(label(tr('Les tags organisent vos clés. Leurs fichiers restent au même endroit.'), 'FooterNote'))
        self.refresh()
        self._load_tag(self._tags[0]['id'] if self._tags else None)

    def set_keys(self, keys):
        self._counts = Counter(key.tag_id for key in keys if key.tag_id)
        for row in range(self._list.count()):
            item = self._list.item(row)
            tag = dict(item.data(Qt.ItemDataRole.UserRole))
            tag['count'] = self._counts[tag['id']]
            item.setData(Qt.ItemDataRole.UserRole, tag)
        self._update_usage()

    def refresh(self):
        self._tags = metadata_store.list_tags()
        self._list.blockSignals(True)
        self._list.clear()
        for tag in self._tags:
            item = QListWidgetItem(tag['label'])
            item.setData(Qt.ItemDataRole.UserRole, dict(tag, count=self._counts[tag['id']]))
            set_translated(item, 'setToolTip', tag['label'])
            self._list.addItem(item)
            if tag['id'] == self._editing_id:
                self._list.setCurrentItem(item)
        self._list.blockSignals(False)
        self._filter()
        if self._editing_id and not any(t['id'] == self._editing_id for t in self._tags):
            self._load_tag(None)
        else:
            self._update_form()

    def _filter(self, *_):
        search = self._search.text().strip().casefold()
        visible = 0
        for row in range(self._list.count()):
            item = self._list.item(row)
            match = search in item.text().casefold()
            item.setHidden(not match)
            visible += match
        set_translated(self._count_label, 'setText', tr('Mes tags · {p0}', p0=len(self._tags)))
        self._list_stack.setCurrentIndex(0 if visible else 1)
        set_translated(self._empty, 'setText', tr('Aucun résultat\nEssayez un autre nom.') if self._tags else
                            tr('Aucun tag\nCréez votre premier tag pour organiser vos clés.'))

    def _dirty(self):
        return (self._name.text().strip(), self._hex.text().upper()) != (
            self._original[0], self._original[1].upper())

    def _selection_changed(self, current, previous):
        if not current:
            return
        target = current.data(Qt.ItemDataRole.UserRole)['id']
        if target == self._editing_id:
            return
        if self._dirty():
            self._list.blockSignals(True)
            self._list.setCurrentItem(previous)
            self._list.blockSignals(False)
            self._ask_discard(lambda: self._load_tag(target))
        else:
            self._load_tag(target)

    def _request_new(self):
        if self._dirty():
            self._ask_discard(lambda: self._load_tag(None))
        else:
            self._load_tag(None)
            self._name.setFocus()

    def _load_tag(self, tag_id):
        tag = next((t for t in self._tags if t['id'] == tag_id), None)
        self._editing_id = tag['id'] if tag else None
        self._original = (tag['label'], tag['color']) if tag else ('', COLOR_PALETTE[12])
        self._loading = True
        set_translated(self._name, 'setText', self._original[0])
        self._palette.set_color(self._original[1])
        set_translated(self._hex, 'setText', self._original[1].upper())
        self._list.blockSignals(True)
        self._list.setCurrentRow(-1)
        for row in range(self._list.count()):
            if self._list.item(row).data(Qt.ItemDataRole.UserRole)['id'] == self._editing_id:
                self._list.setCurrentRow(row)
                break
        self._list.blockSignals(False)
        self._loading = False
        self._cancel_notice()
        self._update_form()

    def _color_changed(self, color):
        self._hex.blockSignals(True)
        set_translated(self._hex, 'setText', color.upper())
        self._hex.blockSignals(False)
        self._update_form()

    def _hex_changed(self, text):
        if re.fullmatch(r'#[0-9a-fA-F]{6}', text):
            self._palette.blockSignals(True)
            self._palette.set_color(text.upper())
            self._palette.blockSignals(False)
        self._update_form()

    def _update_usage(self):
        count = self._counts[self._editing_id]
        set_translated(self._usage, 'setText', tr('Utilisé par {p0} clé{p1}.', p0=count, p1='s' if count != 1 else '') if self._editing_id
                            else tr('Choisissez un nom et une couleur.'))

    def _update_form(self, *_):
        if self._loading:
            return
        valid_color = bool(re.fullmatch(r'#[0-9a-fA-F]{6}', self._hex.text()))
        set_translated(self._editor_title, 'setText', tr('Modifier le tag') if self._editing_id else tr('Créer un tag'))
        set_translated(self._save_btn, 'setText', tr('Enregistrer les modifications') if self._editing_id else tr('Créer le tag'))
        self._save_btn.setEnabled(bool(self._name.text().strip()) and valid_color and self._dirty())
        self._delete_btn.setVisible(bool(self._editing_id))
        self._preview.set_tag(self._name.text().strip() or tr('Votre tag'),
                              self._hex.text() if valid_color else self._palette.selected_color())
        self._feedback.hide()
        self._update_usage()
        if self._pending_action:
            self._cancel_notice()

    def _save(self):
        name, color = self._name.text().strip(), self._hex.text().upper()
        try:
            if self._editing_id:
                metadata_store.update_tag(self._editing_id, name, color)
            else:
                self._editing_id = metadata_store.create_tag(name, color)
        except (ValueError, OSError) as exc:
            set_translated(self._feedback, 'setText', str(exc))
            self._feedback.show()
            self._name.setFocus()
            return
        self.refresh()
        self._load_tag(self._editing_id)
        self.changed.emit()

    def _show_notice(self, title, text, action_text, callback):
        set_translated(self._notice_title, 'setText', title)
        set_translated(self._notice_text, 'setText', text)
        set_translated(self._confirm_btn, 'setText', action_text)
        self._pending_action = callback
        self._save_btn.hide()
        self._delete_btn.hide()
        self._notice.show()
        self._confirm_btn.setFocus()

    def _ask_discard(self, callback):
        self._show_notice(tr('Modifications non enregistrées'),
                          tr('Abandonner ce brouillon pour continuer ?'), tr('Abandonner'), callback)

    def _request_delete(self):
        if not self._editing_id:
            return
        tag = next(t for t in self._tags if t['id'] == self._editing_id)
        count = self._counts[tag['id']]
        self._show_notice(tr('Supprimer « {p0} » ?', p0=tag['label']),
                          tr('Le tag sera retiré de {p0} clé{p1}. Les fichiers des clés sont conservés.', p0=count, p1='s' if count != 1 else ''),
                          tr('Supprimer'), lambda: self._delete(tag['id']))

    def _delete(self, tag_id):
        try:
            metadata_store.delete_tag(tag_id)
        except (ValueError, OSError) as exc:
            set_translated(self._feedback, 'setText', str(exc))
            self._feedback.show()
            return
        self._editing_id = None
        self.refresh()
        self._load_tag(self._tags[0]['id'] if self._tags else None)
        self.changed.emit()

    def _cancel_notice(self):
        self._pending_action = None
        self._notice.hide()
        self._save_btn.show()
        self._delete_btn.setVisible(bool(self._editing_id))

    def _confirm_notice(self):
        action = self._pending_action
        self._cancel_notice()
        if action:
            action()
