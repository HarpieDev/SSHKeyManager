from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core import metadata_store
from ui.theme import chip_colors
from ui.widgets.tags import ColorPalettePicker
from ui.widgets.rounded_combo import RoundedComboBox
from ui.components import icon, label
from ui.tag_page import TagPreview


class TagCreateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tag_id = ""
        self.setWindowTitle("Nouveau tag")
        self.setFixedWidth(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(label("Nouveau tag", "SectionTitle"))
        layout.addWidget(label("Un nom et une couleur pour organiser vos clés."))

        self._name = QLineEdit()
        self._name.setPlaceholderText("Nom du tag")
        layout.addWidget(self._name)

        layout.addWidget(QLabel("Couleur"))
        self._palette = ColorPalettePicker()
        layout.addWidget(self._palette)
        self._preview_chip = TagPreview()
        layout.addWidget(self._preview_chip)
        self._name.textChanged.connect(self._update_preview)
        self._palette.color_changed.connect(self._update_preview)
        self._update_preview()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Créer")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("PrimaryBtn")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self._on_create)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_preview(self, *_):
        self._preview_chip.set_tag(self._name.text().strip() or "Votre tag", self._palette.selected_color())

    def _on_create(self) -> None:
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "Tag", "Indiquez un nom.")
            return
        try:
            self._tag_id = metadata_store.create_tag(name, self._palette.selected_color())
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Tag", str(exc))
            return
        self.accept()

    def created_tag_id(self) -> str:
        return self._tag_id


class TagAssignWidget(QWidget):
    """Sélection compacte d'un tag — une seule ligne."""

    tag_applied = Signal(str)

    def __init__(self, initial_tag_id: str = "", parent=None, *, show_apply=True):
        super().__init__(parent)
        self._selected_id = initial_tag_id or ""

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(8)

        self._combo = RoundedComboBox()
        self._combo.setMinimumHeight(34)
        self._combo.currentIndexChanged.connect(self._on_combo_changed)
        row.addWidget(self._combo, stretch=1)

        apply_btn = QPushButton("Appliquer")
        apply_btn.setObjectName("SecondaryBtn")
        apply_btn.setMinimumHeight(38)
        apply_btn.setVisible(show_apply)
        apply_btn.clicked.connect(lambda: self.tag_applied.emit(self._selected_id))
        row.addWidget(apply_btn)

        new_btn = QPushButton("Nouveau…")
        new_btn.setObjectName("SecondaryBtn")
        new_btn.setMinimumHeight(38)
        new_btn.clicked.connect(self._on_new_tag)
        row.addWidget(new_btn)
        root.addLayout(row)

        self._preview = QLabel("Aucun tag")
        self._preview.setStyleSheet("color: #A5A5B1; font-size: 12px;")
        root.addWidget(self._preview, alignment=Qt.AlignmentFlag.AlignLeft)

        self.reload_tags()

    def reload_tags(self) -> None:
        current = self._selected_id
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItem("— Aucun tag —", "")
        for tag in metadata_store.list_tags():
            _, fg, _ = chip_colors(tag["color"])
            self._combo.addItem(icon("tag", fg, 16), tag["label"], tag["id"])
        idx = self._combo.findData(current)
        self._combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._combo.blockSignals(False)
        self._selected_id = self._combo.currentData() or ""
        self._update_preview()

    def _on_combo_changed(self) -> None:
        self._selected_id = self._combo.currentData() or ""
        self._update_preview()

    def _on_new_tag(self) -> None:
        dialog = TagCreateDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._selected_id = dialog.created_tag_id()
        self.reload_tags()
        self.tag_applied.emit(self._selected_id)

    def _update_preview(self) -> None:
        if not self._selected_id:
            self._preview.setText("Aucun tag")
            self._preview.setStyleSheet("color: #A5A5B1; font-size: 12px;")
            return
        tag = metadata_store.get_tag(self._selected_id)
        if not tag:
            return
        bg, fg, border = chip_colors(tag["color"])
        self._preview.setText(tag["label"])
        self._preview.setStyleSheet(
            f"color: {fg}; background: {bg}; border: 1px solid {border}; "
            f"border-radius: 10px; padding: 2px 10px; font-weight: 600; font-size: 12px;"
        )

    def selected_tag_id(self) -> str:
        return self._selected_id
