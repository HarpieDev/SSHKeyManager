"""Local tool dialogs using the same visual language as the key library."""
from core.i18n import tr
from ui.language import set_translated, localized
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QListWidget, QListWidgetItem, QMessageBox, QTextEdit, QVBoxLayout

from core import ssh_manager
from ui.components import button, dialog_header, label
from ui.tasks import BackgroundMixin


class AgentDialog(QDialog):
    def __init__(self, text: str, error: str, parent=None):
        super().__init__(parent)
        set_translated(self, 'setWindowTitle', "SSH Agent")
        self.resize(660, 460)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(18)
        layout.addWidget(dialog_header("SSH Agent", tr('Les identités actuellement chargées dans l’agent Windows.'), "terminal"))
        content = QTextEdit()
        content.setReadOnly(True)
        set_translated(content, 'setAccessibleName', tr('État et clés de SSH Agent'))
        content.setPlainText(error or text or tr('Aucune identité chargée.'))
        layout.addWidget(content, 1)
        layout.addWidget(label(tr('Ajoutez ou retirez une clé depuis son onglet Connexion. Le service OpenSSH Authentication Agent doit être actif.'), "SecurityNote"))
        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(button(tr('Fermer'), self.accept))
        layout.addLayout(actions)


class TrashDialog(BackgroundMixin, QDialog):
    def __init__(self, items: list[dict], parent=None):
        super().__init__(parent)
        set_translated(self, 'setWindowTitle', tr('Corbeille Harpie'))
        self.resize(640, 510)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(18)
        layout.addWidget(dialog_header(tr('Corbeille'), tr('Retrouvez et restaurez vos identités supprimées.'), "trash", "pink"))
        self._list = QListWidget()
        self._list.setObjectName("TrashList")
        set_translated(self._list, 'setAccessibleName', tr('Clés récupérables'))
        for item in items:
            stamp = item['deleted_at'][:19].replace('T', ' ')
            row = localized(QListWidgetItem(), tr('{p0}\nSupprimée le {p1}', p0=item['name'], p1=stamp))
            row.setData(Qt.ItemDataRole.UserRole, item['id'])
            self._list.addItem(row)
        layout.addWidget(self._list, 1)
        self._empty = label(tr('Votre corbeille est vide. Les clés supprimées apparaîtront ici.'), "SecurityNote")
        self._empty.setVisible(not items)
        layout.addWidget(self._empty)
        layout.addWidget(label(tr('La restauration conserve les tags et les références SSH. Une clé existante ne sera jamais écrasée.'), "FooterNote"))
        actions = QHBoxLayout()
        actions.addWidget(button(tr('Fermer'), self.reject))
        actions.addStretch()
        self._restore_btn = button(tr('Restaurer la clé'), self._restore, "PrimaryBtn", "refresh")
        actions.addWidget(self._restore_btn)
        layout.addLayout(actions)
        self._list.currentItemChanged.connect(self._selection_changed)
        self._list.setCurrentRow(0)
        self._selection_changed()

    def _selection_changed(self, *args):
        self._restore_btn.setEnabled(self._list.currentItem() is not None)

    def _restore(self):
        item = self._list.currentItem()
        if item is None:
            return
        trash_id = item.data(Qt.ItemDataRole.UserRole)
        def completed(result):
            ok, error = result
            if ok:
                self.accept()
            else:
                QMessageBox.warning(self, tr('Restauration impossible'), error)
        self.run_task(lambda: ssh_manager.restore_deleted_key(trash_id), completed)
