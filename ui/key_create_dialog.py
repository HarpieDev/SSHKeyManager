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
from ui.components import label, field


class KeyCreateDialog(BackgroundMixin, QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouvelle clé SSH")
        self.resize(640, 760)
        self.setMinimumSize(560, 550)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(12)
        layout.addWidget(label("NOUVELLE CLÉ", "Eyebrow"))
        layout.addWidget(label("Créer une clé SSH", "AppTitle"))
        layout.addWidget(label("Une nouvelle identité pour vos serveurs et services."))
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        self._name = QLineEdit()
        self._name.setPlaceholderText("ex. vps_production")
        self._comment = QLineEdit()
        self._comment.setPlaceholderText("À quoi servira cette clé ?")
        self._type = QComboBox()
        self._type.addItem("Ed25519", "ed25519")
        self._type.addItem("RSA 4096", "rsa")
        self._passphrase = QLineEdit()
        self._passphrase.setEchoMode(QLineEdit.EchoMode.Password)
        self._passphrase.setPlaceholderText("Optionnelle")
        self._confirm = QLineEdit()
        self._confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm.setPlaceholderText("Répéter la passphrase")
        self._tag_widget = TagAssignWidget(show_apply=False)

        page = QWidget()
        inner = QVBoxLayout(page)
        inner.setContentsMargins(24, 24, 24, 24)
        inner.setSpacing(14)
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(field("Nom de la clé", self._name), 2)
        row.addWidget(field("Algorithme", self._type), 1)
        inner.addLayout(row)
        inner.addWidget(label("Ed25519 offre des clés compactes et convient à la plupart des usages."))
        inner.addWidget(field("Commentaire", self._comment))
        inner.addWidget(field("Tag", self._tag_widget))
        inner.addSpacing(6)
        inner.addWidget(label("Protéger la clé", "ProtectionTitle"))
        inner.addWidget(label("La passphrase protège le fichier privé. Vous pouvez aussi laisser ces champs vides."))
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(field("Passphrase", self._passphrase))
        row.addWidget(field("Confirmation", self._confirm))
        inner.addLayout(row)
        inner.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        tabs.addTab(scroll, "Identité et protection")

        connection = QWidget()
        form = QVBoxLayout(connection)
        form.setContentsMargins(24, 24, 24, 24)
        form.setSpacing(18)
        form.addWidget(label("Préparer une connexion", "SectionTitle"))
        form.addWidget(label("Optionnel : associez cette clé à un serveur. Vous pourrez compléter ces informations plus tard."))
        self._host = QLineEdit()
        self._host.setPlaceholderText("192.168.1.10 ou mon-vps.com")
        self._user = QLineEdit("root")
        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(22)
        form.addWidget(field("Serveur", self._host))
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(field("Utilisateur SSH", self._user), 2)
        row.addWidget(field("Port", self._port), 1)
        form.addLayout(row)
        form.addWidget(label("Après création, ajoutez la clé publique au serveur pour autoriser la connexion."))
        form.addStretch()
        tabs.addTab(connection, "Connexion optionnelle")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Créer la clé")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("PrimaryBtn")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
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
            QMessageBox.warning(self, "Nom invalide", err)
            return

        if host and not user:
            QMessageBox.warning(self, "VPS", "Indiquez l'utilisateur SSH (ex. root).")
            return

        if passphrase != confirm:
            QMessageBox.warning(self, "Passphrase", "Les passphrases ne correspondent pas.")
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
                    warnings.append(f"Tag non enregistré : {exc}")
            if host:
                ok, err = ssh_manager.set_config_entry(name, host, user, port)
                if not ok:
                    warnings.append(f"Connexion non configurée : {err}")
            return True, "", warnings

        def completed(result):
            ok, err, warnings = result
            self._passphrase.clear()
            self._confirm.clear()
            if not ok:
                QMessageBox.warning(self, "Création impossible", err)
                return
            if warnings:
                QMessageBox.warning(self, "Clé créée", "\n".join(warnings))
            self.accept()

        self.run_task(create, completed)
