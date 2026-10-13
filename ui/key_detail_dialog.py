from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QGuiApplication, QMouseEvent
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QInputDialog,
    QFileDialog,
    QFormLayout,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QTabWidget,
    QWidget,
)
from pathlib import Path

from core import metadata_store, ssh_manager
from core.ssh_manager import SshKey
from ui.theme import tag_display
from ui.widgets.tag_dialog import TagAssignWidget
from ui.tasks import BackgroundMixin
from ui.components import label, field, button, key_type_name, dialog_header


def _info_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("color: #EEEEF2; background: transparent; font-size: 13px;")
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


class PublicKeyBlock(QTextEdit):
    """Clé publique sélectionnable, sans contrainte liée à sa longueur."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.set_key_text(text)
        self.setFixedHeight(92)
        self.setToolTip("Clé publique : sélectionnez le texte ou utilisez le bouton Copier.")

    def set_key_text(self, text: str) -> None:
        self._full_text = text
        self.setPlainText(text)


class KeyDetailDialog(BackgroundMixin, QDialog):
    def __init__(self, key: SshKey, parent=None):
        super().__init__(parent)
        self._key = key
        self.setWindowTitle(f"Gérer — {key.name}")
        self.resize(720, 820)
        self.setMinimumSize(580, 540)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(12)
        layout.addWidget(label("DÉTAILS DE LA CLÉ", "Eyebrow"))
        protection = "Protégée par passphrase" if key.encrypted else "Sans passphrase" if key.has_private else "Clé publique seule"
        layout.addWidget(dialog_header(key.name, f"{key_type_name(key.key_type)}  ·  {protection}  ·  {key.created_at:%d/%m/%Y}"))
        if key.warning:
            warning = label(key.warning)
            warning.setStyleSheet("color: #F0B779; background: #372B22; border: 1px solid #543D29; border-radius: 12px; padding: 14px;")
            layout.addWidget(warning)
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs, 1)

        def page(title):
            widget = QWidget()
            inner = QVBoxLayout(widget)
            inner.setContentsMargins(24, 20, 24, 20)
            inner.setSpacing(10)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(widget)
            self._tabs.addTab(scroll, title)
            return inner

        overview = page("Vue d’ensemble")
        overview.addWidget(label("Empreinte SHA256", "FieldLabel"))
        fingerprint = _info_label(key.fingerprint_sha256 or "—")
        fingerprint.setObjectName("Fingerprint")
        overview.addWidget(fingerprint)
        self._comment = QLineEdit(key.comment or "")
        self._comment.setPlaceholderText("Commentaire de la clé")
        overview.addWidget(label("Commentaire", "FieldLabel"))
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self._comment, 1)
        row.addWidget(button("Enregistrer", self._on_save_comment))
        overview.addLayout(row)
        self._tag_widget = TagAssignWidget(key.tag_id)
        self._tag_widget.tag_applied.connect(self._on_tag_applied)
        overview.addWidget(field("Tag", self._tag_widget))
        overview.addWidget(label("Clé publique", "FieldLabel"))
        self._public_key = PublicKeyBlock(key.public_key_text or "—")
        overview.addWidget(self._public_key)
        overview.addWidget(label("À ajouter sur votre serveur ou votre compte GitHub."))
        overview.addWidget(label("Fichier local", "FieldLabel"))
        overview.addWidget(_info_label(str(key.private_path if key.has_private else key.public_path)))
        overview.addStretch()

        connection_layout = page("Connexion")
        connection_layout.addWidget(label("Connexion au serveur", "ConnectionTitle"))
        connection_layout.addWidget(label("Enregistrez l’adresse et l’utilisateur avant de vous connecter."))
        try:
            connection = ssh_manager.get_config_entry(key.name)
        except (OSError, ValueError, UnicodeError):
            connection = {}
        self._host = QLineEdit(connection.get("hostname", ""))
        self._host.setPlaceholderText("IP ou nom du serveur")
        self._user = QLineEdit(connection.get("user", "root"))
        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        try:
            self._port.setValue(int(connection.get("port", "22")))
        except ValueError:
            self._port.setValue(22)
        connection_layout.addWidget(field("Serveur", self._host))
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(field("Utilisateur SSH", self._user), 2)
        row.addWidget(field("Port", self._port), 1)
        connection_layout.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(button("Enregistrer", self._on_save_connection))
        connect_btn = button("Se connecter", self._on_connect, "PrimaryBtn", "terminal")
        connect_btn.setEnabled(key.has_private)
        row.addWidget(connect_btn)
        connection_layout.addLayout(row)
        connection_layout.addSpacing(20)
        connection_layout.addWidget(label("SSH Agent", "SectionTitle"))
        connection_layout.addWidget(label("Chargez la clé dans l’agent pour éviter de saisir sa passphrase à chaque connexion."))
        row = QHBoxLayout()
        add_btn = button("Ajouter à l’agent", self._on_agent_add, symbol="plus")
        add_btn.setEnabled(key.has_private)
        row.addWidget(add_btn)
        row.addWidget(button("Retirer de l’agent", self._on_agent_remove))
        connection_layout.addLayout(row)
        connection_layout.addStretch()

        security = page("Sécurité et fichiers")
        security.addWidget(label("Protection & vérification", "SecurityTitle"))
        security.addWidget(label("Contrôlez la paire de clés, sa passphrase et les droits du fichier privé."))
        grid = QGridLayout()
        grid.setSpacing(10)
        for i, (text, handler) in enumerate((("Vérifier la clé", self._on_verify), ("Changer la passphrase", self._on_passphrase), ("Réparer la clé publique", self._on_repair), ("Protéger le fichier", self._on_permissions))):
            action = button(text, handler)
            action.setEnabled(key.has_private)
            grid.addWidget(action, i // 2, i % 2)
        security.addLayout(grid)
        security.addSpacing(8)
        security.addWidget(label("Export", "SectionTitle"))
        row = QHBoxLayout()
        for text, private in (("Exporter publique", False), ("Exporter privée", True)):
            action = button(text, lambda checked=False, private=private: self._on_export(private))
            action.setEnabled(key.has_private if private else bool(key.public_key_text))
            row.addWidget(action)
        security.addLayout(row)
        security.addSpacing(8)
        self._new_name = QLineEdit()
        self._new_name.setPlaceholderText("Nouveau nom")
        security.addWidget(label("Renommer la clé", "FieldLabel"))
        row = QHBoxLayout()
        row.addWidget(self._new_name, 1)
        row.addWidget(button("Renommer", self._on_rename))
        security.addLayout(row)
        security.addStretch()
        security.addWidget(label("La suppression déplace la clé dans la corbeille Harpie. Elle reste récupérable."))
        security.addWidget(button("Déplacer dans la corbeille", self._on_delete, "DangerBtn", "trash"))

        actions = QHBoxLayout()
        copy_btn = button("Copier la clé publique", self._on_copy, "PrimaryBtn", "copy")
        copy_btn.setEnabled(bool(key.public_key_text))
        actions.addWidget(copy_btn)
        actions.addStretch()
        actions.addWidget(button("Fermer", self.accept))
        layout.addLayout(actions)

    def _on_tag_applied(self, tag_id: str) -> None:
        try:
            metadata_store.set_key_tag(self._key.name, tag_id)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Tag", str(exc))
            return
        if tag_id:
            tag = metadata_store.get_tag(tag_id)
            if tag:
                self._key.tag_id = tag_id
                self._key.tag_label = tag["label"]
                self._key.tag_color = tag["color"]
        else:
            self._key.tag_id = ""
            self._key.tag_label = ""
            self._key.tag_color = ""
        label = tag_display(self._key.tag_label) if self._key.tag_label else "Aucun"
        if self.parent() and hasattr(self.parent(), "statusBar"):
            self.parent().statusBar().showMessage(f"Tag appliqué : {label}", 2500)

    def _on_copy(self) -> None:
        text, err = ssh_manager.read_public_key(self._key.name)
        if err:
            QMessageBox.warning(self, "Erreur", err)
            return
        QGuiApplication.clipboard().setText(text)
        if self.parent() and hasattr(self.parent(), "statusBar"):
            self.parent().statusBar().showMessage("Clé publique copiée", 2500)

    def _on_save_comment(self) -> None:
        comment = self._comment.text().strip()
        self.run_task(lambda: ssh_manager.update_comment(self._key.name, comment), self._mutation_finished)

    def _on_rename(self) -> None:
        new_name = self._new_name.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Renommer", "Indiquez un nouveau nom.")
            return
        self.run_task(lambda: ssh_manager.rename_key(self._key.name, new_name), self._mutation_finished)

    def _on_delete(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirmer la suppression",
            f"Déplacer « {self._key.name} » dans la corbeille Harpie ?\nVous pourrez la restaurer depuis la Corbeille.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.run_task(lambda: ssh_manager.delete_key(self._key.name), self._mutation_finished)

    def _mutation_finished(self, result):
        ok, error = result
        if ok:
            self.accept()
        else:
            QMessageBox.warning(self, "Opération impossible", error)

    def _on_save_connection(self):
        host, user, port = self._host.text().strip(), self._user.text().strip(), self._port.value()
        self.run_task(lambda: ssh_manager.set_config_entry(self._key.name, host, user, port), self._mutation_finished)

    def _on_connect(self):
        try:
            ssh_manager.connect(self._key.name)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Connexion", str(exc))

    def _on_agent_add(self):
        try:
            ssh_manager.add_to_agent(self._key.name)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "SSH Agent", str(exc))

    def _on_agent_remove(self):
        self.run_task(lambda: ssh_manager.remove_from_agent(self._key.name), self._mutation_finished)

    def _on_permissions(self):
        self.run_task(lambda: ssh_manager.fix_permissions(self._key.name), self._mutation_finished)

    def _on_repair(self):
        def completed(result):
            ok, error = result
            if ok:
                self.accept()
            elif "passphrase" in error.lower():
                password, accepted = QInputDialog.getText(self, "Clé chiffrée", "Passphrase", QLineEdit.EchoMode.Password)
                if accepted:
                    self.run_task(lambda: ssh_manager.repair_public_key(self._key.name, password), completed)
            else:
                QMessageBox.warning(self, "Réparation impossible", error)
        self.run_task(lambda: ssh_manager.repair_public_key(self._key.name), completed)

    def _on_export(self, private: bool):
        if private and QMessageBox.question(self, "Exporter la clé privée", "Exporter la clé privée dans un fichier local ?\nConservez ce fichier à l'abri : il permet de vous authentifier.",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        destination, _ = QFileDialog.getSaveFileName(self, "Exporter la clé", self._key.name + ("" if private else ".pub"))
        if not destination:
            return
        def completed(result):
            ok, error = result
            if ok:
                QMessageBox.information(self, "Export", "Clé exportée.")
            else:
                QMessageBox.warning(self, "Export impossible", error)
        self.run_task(lambda: ssh_manager.export_key(self._key.name, Path(destination), private), completed)

    def _on_verify(self):
        def completed(result):
            ok, error = result
            if ok:
                QMessageBox.information(self, "Vérification", "Clé privée valide et clé publique correspondante.")
            elif "passphrase" in error.lower():
                password, accepted = QInputDialog.getText(self, "Clé chiffrée", "Passphrase", QLineEdit.EchoMode.Password)
                if accepted:
                    self.run_task(lambda: ssh_manager.validate_key(self._key.name, password), completed)
            else:
                QMessageBox.warning(self, "Vérification", error)
        self.run_task(lambda: ssh_manager.validate_key(self._key.name), completed)

    def _on_passphrase(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Changer la passphrase")
        dialog.setMinimumWidth(540)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(18)
        layout.addWidget(dialog_header("Changer la passphrase", "Mettez à jour la protection du fichier privé.", "lock", "purple"))
        form = QVBoxLayout()
        form.setSpacing(14)
        fields = []
        for caption in ("Passphrase actuelle (si protégée)", "Nouvelle passphrase (optionnelle)", "Confirmer la nouvelle passphrase"):
            control = QLineEdit()
            control.setEchoMode(QLineEdit.EchoMode.Password)
            fields.append(control)
            form.addWidget(field(caption, control))
        layout.addLayout(form)
        layout.addWidget(label("Laisser la nouvelle passphrase vide retire la protection de la clé.", "SecurityNote"))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Enregistrer")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("PrimaryBtn")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        layout.addWidget(buttons)
        def confirm():
            if fields[1].text() != fields[2].text():
                QMessageBox.warning(dialog, "Passphrase", "Les passphrases ne correspondent pas.")
                return
            dialog.accept()
        buttons.accepted.connect(confirm)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            old, new = fields[0].text(), fields[1].text()
            self.run_task(lambda: ssh_manager.change_passphrase(self._key.name, old, new), self._mutation_finished)
        for control in fields:
            control.clear()
