from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core import metadata_store
from ui.theme import COLOR_PALETTE, chip_colors


class ColorPalettePicker(QWidget):
    color_changed = Signal(str)

    def __init__(self, initial: str = COLOR_PALETTE[12], parent=None):
        super().__init__(parent)
        self._selected = initial
        self._buttons: dict[str, QPushButton] = {}

        grid = QGridLayout(self)
        self._grid = grid
        self._columns = 10
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        grid.setSpacing(6)
        grid.setContentsMargins(0, 0, 0, 0)

        cols = 10
        for i, color in enumerate(COLOR_PALETTE):
            btn = QPushButton()
            btn.setFixedSize(26, 26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(color)
            btn.clicked.connect(lambda checked=False, c=color: self._select(c))
            self._buttons[color] = btn
            grid.addWidget(btn, i // cols, i % cols)

        self.setFixedHeight(62)
        self.set_color(initial)

    def _style_btn(self, color: str, selected: bool) -> None:
        border = "2px solid #F5F5F7" if selected else "2px solid #48484A"
        self._buttons[color].setStyleSheet(
            f"QPushButton {{ background-color: {color}; border-radius: 13px; border: {border}; padding: 0; min-height: 0; min-width: 0; }}"
        )

    def _select(self, color: str) -> None:
        self._selected = color
        for c in self._buttons:
            self._style_btn(c, c.casefold() == color.casefold())
        self.color_changed.emit(color)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = event.size().width()
        columns = 10 if width >= 314 else min(8, max(1, (width + 6) // 32))
        if columns != self._columns:
            self._columns = columns
            for i, btn in enumerate(self._buttons.values()):
                self._grid.removeWidget(btn)
                self._grid.addWidget(btn, i // columns, i % columns)
            rows = (len(self._buttons) + columns - 1) // columns
            self.setFixedHeight(rows * 26 + (rows - 1) * 6 + 4)

    def set_color(self, color: str) -> None:
        self._select(color)

    def selected_color(self) -> str:
        return self._selected


class TagEditor(QWidget):
    """Sélection ou création d'un tag avec palette de couleurs."""

    tag_applied = Signal(str)

    def __init__(self, initial_tag_id: str = "", parent=None):
        super().__init__(parent)
        self._selected_id = initial_tag_id or ""

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # --- Tag existant ---
        existing = QFrame()
        existing.setStyleSheet(
            "QFrame { background: #252529; border: 1px solid #48424F; border-radius: 8px; }"
        )
        existing_layout = QVBoxLayout(existing)
        existing_layout.setContentsMargins(12, 10, 12, 10)
        existing_layout.setSpacing(8)

        existing_layout.addWidget(self._section_label("Tag existant"))

        row = QHBoxLayout()
        row.setSpacing(8)
        self._combo = QComboBox()
        self._combo.setMinimumHeight(36)
        self._combo.currentIndexChanged.connect(self._on_combo_changed)
        row.addWidget(self._combo, stretch=1)

        apply_btn = QPushButton("Appliquer")
        apply_btn.setObjectName("SecondaryBtn")
        apply_btn.setFixedHeight(36)
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_btn.clicked.connect(self._apply_selection)
        row.addWidget(apply_btn)
        existing_layout.addLayout(row)

        self._current_preview = QLabel("Aucun tag")
        self._current_preview.setStyleSheet("color: #A5A5B1; font-size: 12px;")
        existing_layout.addWidget(self._current_preview)
        root.addWidget(existing)

        # --- Nouveau tag ---
        create_frame = QFrame()
        create_frame.setStyleSheet(
            "QFrame { background: #252529; border: 1px solid #48424F; border-radius: 8px; }"
        )
        create_layout = QVBoxLayout(create_frame)
        create_layout.setContentsMargins(12, 10, 12, 10)
        create_layout.setSpacing(8)

        create_layout.addWidget(self._section_label("Créer un nouveau tag"))

        self._new_name = QLineEdit()
        self._new_name.setPlaceholderText("Nom du tag (ex. Test, Production…)")
        self._new_name.setMinimumHeight(36)
        create_layout.addWidget(self._new_name)

        create_layout.addWidget(self._section_label("Couleur"))
        self._palette = ColorPalettePicker()
        create_layout.addWidget(self._palette)

        create_btn = QPushButton("Créer et appliquer")
        create_btn.setObjectName("PrimaryBtn")
        create_btn.setMinimumHeight(36)
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.clicked.connect(self._on_create)
        create_layout.addWidget(create_btn)
        root.addWidget(create_frame)

        self.reload_tags()
        self._update_preview()

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("color: #BAB5C8; font-size: 12px; font-weight: 600; border: none;")
        return label

    def reload_tags(self) -> None:
        current = self._selected_id
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItem("— Aucun tag —", "")
        for tag in metadata_store.list_tags():
            self._combo.addItem(tag["label"], tag["id"])
        idx = self._combo.findData(current)
        self._combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._combo.blockSignals(False)
        self._selected_id = self._combo.currentData() or ""
        self._update_preview()

    def _on_combo_changed(self) -> None:
        self._selected_id = self._combo.currentData() or ""
        self._update_preview()

    def _apply_selection(self) -> None:
        self.tag_applied.emit(self._selected_id)

    def _on_create(self) -> None:
        name = self._new_name.text().strip()
        if not name:
            QMessageBox.warning(self.window(), "Tag", "Indiquez un nom pour le tag.")
            return
        color = self._palette.selected_color()
        try:
            tag_id = metadata_store.create_tag(name, color)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self.window(), "Tag", str(exc))
            return
        self._new_name.clear()
        self._selected_id = tag_id
        self.reload_tags()
        self.tag_applied.emit(tag_id)

    def _update_preview(self) -> None:
        if not self._selected_id:
            self._current_preview.setText("Aucun tag sélectionné")
            self._current_preview.setStyleSheet("color: #A5A5B1; font-size: 12px;")
            return
        tag = metadata_store.get_tag(self._selected_id)
        if not tag:
            self._current_preview.setText("Aucun tag sélectionné")
            return
        bg, fg, border = chip_colors(tag["color"])
        self._current_preview.setText(tag["label"])
        self._current_preview.setStyleSheet(
            f"color: {fg}; background-color: {bg}; border: 1px solid {border}; "
            f"border-radius: 10px; padding: 4px 10px; font-weight: 600; font-size: 12px;"
        )

    def selected_tag_id(self) -> str:
        return self._selected_id or ""


class TagFilterBar(QWidget):
    filter_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = "all"
        self._buttons: dict[str, QPushButton] = {}
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self.rebuild()

    def rebuild(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._buttons.clear()

        all_btn = self._make_btn("Tous", "all", "#232A35", "#B8D6FF", "#3C5981")
        all_btn.setChecked(self._active == "all")
        self._layout.addWidget(all_btn)
        self._buttons["all"] = all_btn

        tags = metadata_store.list_tags()
        if self._active != "all" and self._active not in {tag["id"] for tag in tags}:
            self._active = "all"
            all_btn.setChecked(True)
            self.filter_changed.emit("all")
        for tag in tags:
            bg, fg, border = chip_colors(tag["color"])
            btn = self._make_btn(tag["label"], tag["id"], bg, fg, border)
            btn.setChecked(self._active == tag["id"])
            self._layout.addWidget(btn)
            self._buttons[tag["id"]] = btn

        self._layout.addStretch()

    def _make_btn(self, text: str, tag_id: str, bg: str, fg: str, border: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(30)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {bg}; color: {fg}; "
            f"border: 1px solid transparent; border-radius: 15px; "
            f"padding: 4px 11px; min-height: 18px; font-size: 11px; font-weight: 500; }}"
            f"QPushButton:hover {{ border-color: {border}; }}"
            f"QPushButton:checked {{ border-color: {fg}; }}"
            f"QPushButton:focus {{ border-color: {fg}; }}"
        )
        btn.clicked.connect(lambda: self._on_click(tag_id))
        return btn

    def _on_click(self, tag_id: str) -> None:
        self._active = tag_id
        for tid, btn in self._buttons.items():
            btn.setChecked(tid == tag_id)
        self.filter_changed.emit(tag_id)
