from core.i18n import tr
from ui.language import set_translated, add_translated_tab
from PySide6.QtWidgets import (
    QDialog,
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QScrollArea,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTabWidget,
    QWidget,
)

from core import metadata_store, ssh_manager
from ui.widgets.tag_dialog import TagAssignWidget
from ui.tasks import BackgroundMixin
from ui.components import label, field, dialog_header


class KeyCreateDialog(BackgroundMixin, QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        set_translated(self, 'setWindowTitle', tr('Nouvelle clé SSH'))
        self.resize(680, 770)
        self.setMinimumSize(560, 550)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(12)
        layout.addWidget(label(tr('BIBLIOTHÈQUE  /  NOUVELLE IDENTITÉ'), "Eyebrow"))
        layout.addWidget(dialog_header(tr('Créer une clé SSH'), tr('Une identité locale pour vos serveurs et services.'), "plus"))
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        self._name = QLineEdit()
        set_translated(self._name, 'setPlaceholderText', tr('ex. vps_production'))
        self._comment = QLineEdit()
        set_translated(self._comment, 'setPlaceholderText', tr('À quoi servira cette clé ?'))
        self._type = QComboBox()
        self._type.addItem("Ed25519", "ed25519")
        self._type.addItem("RSA 4096", "rsa")
        self._passphrase = QLineEdit()
        self._passphrase.setEchoMode(QLineEdit.EchoMode.Password)
        set_translated(self._passphrase, 'setPlaceholderText', tr('Optionnelle'))
        self._confirm = QLineEdit()
        self._confirm.setEchoMode(QLineEdit.EchoMode.Password)
        set_translated(self._confirm, 'setPlaceholderText', tr('Répéter la passphrase'))
        self._tag_widget = TagAssignWidget(show_apply=False)

        page = QWidget()
        inner = QVBoxLayout(page)
        inner.setContentsMargins(24, 24, 24, 24)
        inner.setSpacing(14)
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(field(tr('Nom de la clé'), self._name), 2)
        row.addWidget(field(tr('Algorithme'), self._type), 1)
        inner.addLayout(row)
        inner.addWidget(label(tr('Ed25519 : des clés compactes, adaptées à la plupart des usages.'), "SecurityNote"))
        inner.addWidget(field(tr('Commentaire'), self._comment))
        inner.addWidget(field(tr('Tag'), self._tag_widget))
        inner.addSpacing(6)
        inner.addWidget(label(tr('Protéger la clé'), "ProtectionTitle"))
        inner.addWidget(label(tr('La passphrase protège le fichier privé. Vous pouvez aussi laisser ces champs vides.')))
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(field(tr('Passphrase'), self._passphrase))
        row.addWidget(field(tr('Confirmation'), self._confirm))
        inner.addLayout(row)
        inner.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        add_translated_tab(tabs, scroll, tr('Identité et protection'))

        connection = QWidget()
        form = QVBoxLayout(connection)
        form.setContentsMargins(24, 24, 24, 24)
        form.setSpacing(18)
        form.addWidget(label(tr('Préparer une connexion'), "SectionTitle"))
        form.addWidget(label(tr('Optionnel : associez cette clé à un serveur. Vous pourrez compléter ces informations plus tard.')))
        self._host = QLineEdit()
        set_translated(self._host, 'setPlaceholderText', tr('192.168.1.10 ou mon-vps.com'))
        self._user = QLineEdit("root")
        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(22)
        form.addWidget(field(tr('Serveur'), self._host))
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(field(tr('Utilisateur SSH'), self._user), 2)
        row.addWidget(field(tr('Port'), self._port), 1)
        form.addLayout(row)
        form.addWidget(label(tr('Après création, ajoutez la clé publique au serveur pour autoriser la connexion.')))
        form.addStretch()
        add_translated_tab(tabs, connection, tr('Connexion optionnelle'))

        layout.addWidget(label(tr('La clé privée est créée sur cet ordinateur. Aucune donnée n’est envoyée.'), "FooterNote"))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        set_translated(buttons.button(QDialogButtonBox.StandardButton.Ok), 'setText', tr('Créer la clé'))
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("PrimaryBtn")
        set_translated(buttons.button(QDialogButtonBox.StandardButton.Cancel), 'setText', tr('Annuler'))
        buttons.accepted.connect(self._on_create)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._name.setFocus()

    def _on_create(self) -> None:
        name = self._name.text().strip()
        host = self._host.text().strip()
        user = self._user.text().strip()
        comment = self._comment.text().strip()
        passphrase = self._passphrase.text()
        confirm = self._confirm.text()

        valid, err = ssh_manager.validate_key_name(name)
        if not valid:
            QMessageBox.warning(self, tr('Nom invalide'), err)
            return

        if host and not user:
            QMessageBox.warning(self, "VPS", tr("Indiquez l'utilisateur SSH (ex. root)."))
            return

        if passphrase != confirm:
            QMessageBox.warning(self, tr('Passphrase'), tr('Les passphrases ne correspondent pas.'))
            return

        tag_id = self._tag_widget.selected_tag_id()
        kind, port = self._type.currentData(), self._port.value()

        def create():
            ok, err = ssh_manager.create_key(name, comment, passphrase, kind)
            if not ok:
                return False, err, []
            warnings = []
            if tag_id:
                try:
                    metadata_store.set_key_tag(name, tag_id)
                except (OSError, ValueError) as exc:
                    warnings.append(tr('Tag non enregistré : {p0}', p0=exc))
            if host:
                ok, err = ssh_manager.set_config_entry(name, host, user, port)
                if not ok:
                    warnings.append(tr('Connexion non configurée : {p0}', p0=err))
            return True, "", warnings

        def completed(result):
            ok, err, warnings = result
            self._passphrase.clear()
            self._confirm.clear()
            if not ok:
                QMessageBox.warning(self, tr('Création impossible'), err)
                return
            if warnings:
                QMessageBox.warning(self, tr('Clé créée'), "\n".join(warnings))
            self.accept()

        self.run_task(create, completed)
