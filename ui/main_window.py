from pathlib import Path
import webbrowser

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, QSettings
from PySide6.QtGui import QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QStatusBar,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core import ssh_manager, metadata_store
from core.ssh_manager import SshKey
from ui.key_create_dialog import KeyCreateDialog
from ui.key_detail_dialog import KeyDetailDialog
from ui.assets import logo_path
from ui.theme import tag_display, TEXT, WARNING
from ui.widgets.tag_delegate import TagDelegate
from ui.widgets.tags import TagFilterBar
from ui.tasks import BackgroundMixin
from ui.components import button, icon, label, key_type_name, SummaryCard
from ui.widgets.key_delegate import KeyDelegate
from ui.tag_page import TagPage
from ui.window_frame import IntegratedWindow
from version import __version__
from ui.tools_dialog import AgentDialog, TrashDialog


class KeysTableModel(QAbstractTableModel):
    HEADERS = ["Tag", "Nom", "Type", "Commentaire", "Empreinte", "Modifiée le"]

    def __init__(self, keys: list[SshKey] | None = None):
        super().__init__()
        self._keys = keys or []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._keys)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        key = self._keys[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.UserRole:
            return key

        if role == Qt.ItemDataRole.UserRole + 1:
            return key.created_at.timestamp() if col == 5 else self.data(index, Qt.ItemDataRole.DisplayRole)

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return tag_display(key.tag_label) if key.tag_label else ""
            if col == 1:
                return key.name
            if col == 2:
                return key_type_name(key.key_type)
            if col == 3:
                return key.comment
            if col == 4:
                return key.fingerprint_sha256
            if col == 5:
                return key.created_at.strftime("%d/%m/%Y")

        if role == Qt.ItemDataRole.ForegroundRole:
            from PySide6.QtGui import QColor
            if key.warning and col == 1:
                return QColor(WARNING)
            return QColor(TEXT)

        if role == Qt.ItemDataRole.ToolTipRole:
            if key.warning:
                return key.warning
            if col == 0 and key.tag_label:
                return key.tag_label

        return None

    def update_keys(self, keys: list[SshKey]) -> None:
        self.beginResetModel()
        self._keys = keys
        self.endResetModel()

    def key_at(self, row: int) -> SshKey | None:
        if 0 <= row < len(self._keys):
            return self._keys[row]
        return None


class KeysFilterProxyModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._tag_filter = "all"
        self._warnings_only = False

    def set_tag_filter(self, tag_id: str) -> None:
        self.beginFilterChange()
        self._tag_filter = tag_id
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def set_warnings_only(self, enabled: bool) -> None:
        self.beginFilterChange()
        self._warnings_only = enabled
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        if hasattr(model, "key_at"):
            key = model.key_at(source_row)
            if key and self._warnings_only and not key.warning:
                return False
            if key and self._tag_filter != "all" and key.tag_id != self._tag_filter:
                return False
        return super().filterAcceptsRow(source_row, source_parent)


class MainWindow(BackgroundMixin, IntegratedWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Harpie SSH Key Manager")
        icon = QIcon(str(logo_path()))
        if not icon.isNull():
            self.setWindowIcon(icon)
        self.resize(1380, 960)
        self.setMinimumSize(920, 640)
        geometry = QSettings().value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        self.setStatusBar(QStatusBar())
        self.statusBar().setSizeGripEnabled(False)

        self._build_ui()
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._focus_search)
        QShortcut(QKeySequence("F5"), self, activated=self.refresh_keys)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._on_new_key)
        self._check_openssh()
        self.refresh_keys()

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName('WindowCanvas')
        self.setCentralWidget(central)
        frame = QVBoxLayout(central)
        frame.setContentsMargins(8, 8, 8, 8)
        frame.setSpacing(0)
        surface = QFrame()
        surface.setObjectName('AppSurface')
        frame.addWidget(surface)
        root = QHBoxLayout(surface)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())

        content = QWidget()
        layout = QVBoxLayout(content)
        self._content_layout = layout
        layout.setContentsMargins(32, 28, 32, 18)
        layout.setSpacing(18)
        context = QHBoxLayout()
        breadcrumb = label("ESPACE PERSONNEL  /  BIBLIOTHÈQUE", "Eyebrow")
        breadcrumb.setWordWrap(False)
        context.addWidget(breadcrumb)
        context.addStretch()
        local_badge = label("●  Stockage local", "LocalBadge")
        local_badge.setFixedHeight(28)
        context.addWidget(local_badge)
        layout.addLayout(context)
        heading = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(5)
        titles.addWidget(label("Vos clés. Votre espace.", "AppTitle"))
        titles.addWidget(label("Créez, organisez et protégez vos identités SSH."))
        heading.addLayout(titles, 1)
        heading.addWidget(button("Nouvelle clé", self._on_new_key, "PrimaryBtn", "plus"))
        layout.addLayout(heading)

        self._summary_strip = QWidget()
        summary_layout = QHBoxLayout(self._summary_strip)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(14)
        self._summary_total = SummaryCard("Identités SSH", "Bibliothèque", "key", "blue")
        self._summary_protected = SummaryCard("Avec passphrase", "Protection", "lock", "purple")
        self._summary_warnings = SummaryCard("À vérifier", "Diagnostics", "alert", "orange")
        for summary in (self._summary_total, self._summary_protected, self._summary_warnings):
            summary_layout.addWidget(summary, 1)
        layout.addWidget(self._summary_strip)

        self._keys_model = KeysTableModel()
        self._keys_proxy = KeysFilterProxyModel()
        self._keys_proxy.setSourceModel(self._keys_model)
        self._keys_proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._keys_proxy.setFilterKeyColumn(-1)
        self._keys_proxy.setSortRole(Qt.ItemDataRole.UserRole + 1)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        self._search = QLineEdit()
        self._search.setObjectName("SearchField")
        self._search.setMinimumHeight(46)
        self._search.setPlaceholderText("Rechercher un nom, un tag, une empreinte…")
        self._search.setAccessibleName("Rechercher dans les clés SSH")
        self._search.addAction(icon("search"), QLineEdit.ActionPosition.LeadingPosition)
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._keys_proxy.setFilterFixedString)
        toolbar.addWidget(self._search, 1)
        tools = QFrame()
        tools.setObjectName("GlassToolbar")
        tool_layout = QHBoxLayout(tools)
        tool_layout.setContentsMargins(4, 3, 4, 3)
        tool_layout.setSpacing(2)
        tool_layout.addWidget(button("Importer", self._on_import, "ToolbarBtn", "import"))
        self._refresh_btn = button("", self.refresh_keys, "ToolbarBtn", "refresh")
        self._refresh_btn.setFixedSize(40, 40)
        self._refresh_btn.setToolTip("Actualiser les clés · F5")
        self._refresh_btn.setAccessibleName("Actualiser les clés")
        tool_layout.addWidget(self._refresh_btn)
        toolbar.addWidget(tools)
        layout.addLayout(toolbar)

        body = QHBoxLayout()
        body.setSpacing(18)
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 10, 16, 14)
        card_layout.setSpacing(0)
        list_header = QHBoxLayout()
        list_header.setContentsMargins(8, 12, 8, 8)
        self._list_title = label("Toutes les clés", "SectionTitle")
        list_header.addWidget(self._list_title)
        list_header.addStretch()
        self._stat_badge = label("0", "StatBadge")
        list_header.addWidget(self._stat_badge)
        card_layout.addLayout(list_header)
        self._tag_filter = TagFilterBar()
        self._tag_filter.filter_changed.connect(self._on_tag_filter)
        tag_scroll = QScrollArea()
        tag_scroll.setWidget(self._tag_filter)
        tag_scroll.setWidgetResizable(True)
        tag_scroll.setFrameShape(QFrame.Shape.NoFrame)
        tag_scroll.setFixedHeight(48)
        tag_scroll.setContentsMargins(8, 0, 8, 0)
        tag_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        card_layout.addWidget(tag_scroll)

        self._keys_table = QTableView()
        self._keys_table.setModel(self._keys_proxy)
        self._keys_table.setItemDelegateForColumn(0, TagDelegate(self._keys_table))
        self._keys_table.setItemDelegateForColumn(1, KeyDelegate(self._keys_table))
        self._keys_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._keys_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._keys_table.setSortingEnabled(True)
        self._keys_table.setShowGrid(False)
        self._keys_table.setMouseTracking(True)
        self._keys_table.verticalHeader().hide()
        self._keys_table.verticalHeader().setDefaultSectionSize(78)
        self._keys_table.setAccessibleName("Bibliothèque de clés SSH")
        self._keys_table.setColumnHidden(3, True)
        self._keys_table.setColumnHidden(4, True)
        header = self._keys_table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.moveSection(header.visualIndex(1), 0)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col, width in ((0, 106), (2, 82), (5, 100)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(col, width)
        self._keys_table.doubleClicked.connect(self._on_key_double_click)
        self._keys_table.selectionModel().selectionChanged.connect(self._update_preview)
        self._keys_table.sortByColumn(1, Qt.SortOrder.AscendingOrder)
        QShortcut(QKeySequence("Return"), self._keys_table, activated=self._open_selected)

        self._list_stack = QStackedWidget()
        self._list_stack.addWidget(self._keys_table)
        empty = QWidget()
        empty_layout = QVBoxLayout(empty)
        empty_layout.setContentsMargins(30, 40, 30, 40)
        empty_layout.addStretch()
        symbol = QLabel()
        symbol.setPixmap(icon("key", "#6DBBEE", 48).pixmap(48, 48))
        empty_layout.addWidget(symbol, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._empty_title = label("Votre espace est prêt", "SectionTitle")
        self._empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_hint = label("Créez ou importez votre première clé SSH.")
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._empty_title)
        empty_layout.addWidget(self._empty_hint)
        self._empty_actions = QWidget()
        empty_actions = QHBoxLayout(self._empty_actions)
        empty_actions.addStretch()
        empty_actions.addWidget(button("Créer une clé", self._on_new_key, "PrimaryBtn", "plus"))
        empty_actions.addWidget(button("Importer", self._on_import, symbol="import"))
        empty_actions.addStretch()
        empty_layout.addWidget(self._empty_actions)
        empty_layout.addStretch()
        self._list_stack.addWidget(empty)
        card_layout.addWidget(self._list_stack, 1)
        foot = label("Double-clic pour ouvrir les détails  ·  Entrée pour gérer la sélection", "FooterNote")
        foot.setContentsMargins(8, 10, 8, 0)
        card_layout.addWidget(foot)
        body.addWidget(card, 1)
        self._preview_card = self._build_preview()
        body.addWidget(self._preview_card)
        layout.addLayout(body, 1)
        compact = QHBoxLayout()
        compact.addStretch()
        compact.addWidget(self._compact_copy)
        self._compact_detail = button("Gérer cette clé", self._open_selected, symbol="arrow")
        compact.addWidget(self._compact_detail)
        self._compact_actions = QWidget()
        self._compact_actions.setLayout(compact)
        layout.addWidget(self._compact_actions)
        self._compact_actions.hide()
        footer = QHBoxLayout()
        local_note = label("Harpie  ·  Vos clés restent sur cet ordinateur", "FooterNote")
        local_note.setWordWrap(False)
        footer.addWidget(local_note)
        footer.addStretch()
        shortcuts = label("Ctrl + N  Nouvelle clé     ·     Ctrl + F  Rechercher", "FooterNote")
        shortcuts.setWordWrap(False)
        footer.addWidget(shortcuts)
        layout.addLayout(footer)
        self._pages = QStackedWidget()
        self._pages.addWidget(content)
        self._tag_page = None
        root.addWidget(self._pages, 1)
        self._keys_proxy.rowsInserted.connect(self._sync_list)
        self._keys_proxy.rowsRemoved.connect(self._sync_list)
        self._keys_proxy.modelReset.connect(self._sync_list)
        self._keys_proxy.layoutChanged.connect(self._sync_list)
        self._sync_list()
        self._update_preview()

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(216)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 26, 16, 18)
        layout.setSpacing(6)
        brand = QHBoxLayout()
        symbol = QLabel()
        symbol.setPixmap(QIcon(str(logo_path())).pixmap(34, 34))
        brand.addWidget(symbol)
        brand.addWidget(label("Harpie", "Brand"))
        brand.addStretch()
        layout.addLayout(brand)
        layout.addWidget(label("SSH KEY MANAGER", "Eyebrow"))
        layout.addSpacing(32)
        layout.addWidget(label("BIBLIOTHÈQUE", "SidebarSection"))
        self._all_nav = button("Toutes les clés", lambda: self._set_view(False), symbol="grid")
        self._alert_nav = button("À vérifier", lambda: self._set_view(True), symbol="alert")
        self._all_nav.setIcon(icon("grid", "#2197FE", 18))
        self._alert_nav.setIcon(icon("alert", "#E9A76C", 18))
        self._alert_nav.setObjectName("WarningNav")
        for item in (self._all_nav, self._alert_nav):
            item.setCheckable(True)
            layout.addWidget(item)
        self._all_nav.setChecked(True)
        layout.addSpacing(26)
        layout.addWidget(label("OUTILS", "SidebarSection"))
        for title, handler, symbol, color in (
            ("SSH Agent", self._on_agent, "terminal", "#32D2F0"),
            ("Corbeille", self._on_restore, "trash", "#EF89AD"),
            ("Tags", self._on_manage_tags, "tag", "#B88AE9"),
            ("Dossier .ssh", self._on_open_ssh_folder, "folder", "#6DBBEE"),
        ):
            item = button(title, handler)
            item.setIcon(icon(symbol, color, 18))
            if title == "Tags":
                self._tags_nav = item
                item.setCheckable(True)
                item.setObjectName("TagsNav")
            layout.addWidget(item)
        layout.addStretch()
        github = button("GitHub SSH Keys", lambda: webbrowser.open("https://github.com/settings/keys"))
        github.setIcon(icon("arrow", "#AEAEB2", 17))
        layout.addWidget(github)
        layout.addSpacing(12)
        local = QFrame()
        local.setObjectName("LocalCard")
        local.setFixedHeight(94)
        local_layout = QVBoxLayout(local)
        local_layout.setContentsMargins(14, 14, 14, 14)
        local_layout.setSpacing(6)
        local_layout.addWidget(label("●  Espace local", "FieldLabel"))
        local_layout.addWidget(label("Sans compte. Sans cloud.", "FooterNote"))
        local_layout.addWidget(label(f"Harpie  v{__version__}", "FooterNote"))
        layout.addWidget(local)
        return sidebar

    def _build_preview(self):
        card = QFrame()
        card.setObjectName("PreviewCard")
        card.setFixedWidth(286)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        details = QWidget()
        outer = QVBoxLayout(details)
        outer.setContentsMargins(0, 0, 4, 0)
        outer.setSpacing(10)
        caption = QHBoxLayout()
        heading = label("CLÉ SÉLECTIONNÉE", "Eyebrow")
        heading.setWordWrap(False)
        caption.addWidget(heading)
        caption.addStretch()
        caption.addWidget(label("↵", "KeyboardHint"))
        outer.addLayout(caption)
        hero = QFrame()
        hero.setObjectName("PreviewHero")
        hero.setMinimumHeight(136)
        identity = QVBoxLayout(hero)
        identity.setContentsMargins(16, 14, 16, 14)
        identity.setSpacing(8)
        symbol = QLabel()
        symbol.setObjectName("PreviewSymbol")
        symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        symbol.setFixedSize(40, 40)
        symbol.setPixmap(icon("key", "#9CC6FF", 24).pixmap(24, 24))
        identity.addWidget(symbol)
        self._preview_name = label("Sélectionnez une clé", "PreviewTitle")
        self._preview_name.setMinimumWidth(0)
        identity.addWidget(self._preview_name)
        self._preview_state = label("Ses informations apparaîtront ici.", "PreviewState")
        identity.addWidget(self._preview_state)
        outer.addWidget(hero)
        facts = QHBoxLayout()
        facts.setSpacing(12)
        self._preview_values = {}
        for title, caption in (("TYPE", "Algorithme"), ("PROTECTION", "Protection"), ("EMPREINTE", "Empreinte SHA256"), ("MODIFIÉE LE", "Dernière modification")):
            group = QVBoxLayout()
            group.setSpacing(6)
            group.addWidget(label(caption, "DetailCaption"))
            value = label("—", "Fingerprint" if title == "EMPREINTE" else "DetailValue")
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._preview_values[title] = value
            group.addWidget(value)
            if title in ("TYPE", "PROTECTION"):
                facts.addLayout(group, 1)
                if title == "PROTECTION":
                    outer.addLayout(facts)
                    rule = QFrame()
                    rule.setObjectName("Rule")
                    outer.addWidget(rule)
            else:
                outer.addLayout(group)
        outer.addStretch()
        scroll.setWidget(details)
        layout.addWidget(scroll, 1)
        self._copy_btn = button("Copier la clé publique", self._on_copy_public, "TintedBtn", "copy")
        self._copy_btn.setToolTip("Copier uniquement la clé publique. Le fichier privé reste sur cet ordinateur.")
        self._detail_btn = button("Gérer cette clé", self._open_selected, "PrimaryBtn", "arrow")
        layout.addWidget(self._copy_btn)
        layout.addWidget(self._detail_btn)
        self._compact_copy = button("Copier publique", self._on_copy_public, symbol="copy")
        return card

    def _set_view(self, warnings_only):
        self._pages.setCurrentIndex(0)
        self._tags_nav.setChecked(False)
        self._all_nav.setChecked(not warnings_only)
        self._alert_nav.setChecked(warnings_only)
        self._list_title.setText("À vérifier" if warnings_only else "Toutes les clés")
        self._keys_proxy.set_warnings_only(warnings_only)
        self._sync_list()

    def _sync_list(self, *args):
        count = self._keys_proxy.rowCount()
        self._stat_badge.setText(str(count))
        self._list_stack.setCurrentIndex(0 if count else 1)
        total = self._keys_model.rowCount()
        keys = self._keys_model._keys
        self._summary_total.set_count(total)
        self._summary_protected.set_count(sum(bool(key.has_private and key.encrypted) for key in keys))
        self._summary_warnings.set_count(sum(bool(key.warning) for key in keys))
        self._empty_actions.setVisible(not total)
        self._empty_title.setText("Aucun résultat" if total else "Votre espace est prêt")
        self._empty_hint.setText("Essayez une autre recherche ou un autre filtre." if total else "Créez ou importez votre première clé SSH.")
        if count and self._selected_key() is None:
            self._keys_table.selectRow(0)
        self._update_preview()

    def _update_preview(self, *args):
        if not hasattr(self, "_preview_name"):
            return
        key = self._selected_key()
        self._copy_btn.setEnabled(bool(key and key.public_key_text))
        self._detail_btn.setEnabled(key is not None)
        self._compact_copy.setEnabled(bool(key and key.public_key_text))
        if hasattr(self, "_compact_detail"):
            self._compact_detail.setEnabled(key is not None)
        self._preview_name.setText(key.name if key else "Sélectionnez une clé")
        self._preview_name.setToolTip(key.name if key else "")
        self._preview_state.setText((key.warning or key.tag_label or "Clé personnelle") if key else "Ses informations apparaîtront ici.")
        self._preview_state.setStyleSheet("color: #F0B779; font-size: 12px;" if key and key.warning else "color: #B6C8E3; font-size: 12px;")
        values = (key_type_name(key.key_type), "Passphrase" if key.encrypted else "Sans passphrase" if key.has_private else "Publique seule", key.fingerprint_sha256 or "—", key.created_at.strftime("%d/%m/%Y · %H:%M")) if key else ("—",) * 4
        for widget, value in zip(self._preview_values.values(), values):
            widget.setToolTip(value)
            if widget is self._preview_values["EMPREINTE"] and key:
                import textwrap
                value = "\n".join(textwrap.wrap(value, 27))
            widget.setText(value)

    def _open_selected(self):
        indexes = self._keys_table.selectionModel().selectedRows()
        if indexes:
            self._on_key_double_click(indexes[0])

    def _focus_search(self):
        if self._tag_page and self._pages.currentWidget() is self._tag_page:
            self._tag_page._search.setFocus()
        else:
            self._search.setFocus()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_preview_card"):
            self._preview_card.setVisible(event.size().width() >= 1150 and event.size().height() >= 760)
            self._compact_actions.setVisible(event.size().width() < 1150 or event.size().height() < 760)
            compact_height = event.size().height() < 700
            self._summary_strip.setVisible(not compact_height)
            self._content_layout.setSpacing(14 if compact_height else 18)
            if compact_height:
                self._content_layout.setContentsMargins(24, 22, 24, 14)
            else:
                self._content_layout.setContentsMargins(32, 28, 32, 18)

    def _check_openssh(self) -> None:
        ok, err = ssh_manager.check_openssh_available()
        if not ok:
            self.statusBar().showMessage(err, 12000)

    def _on_tag_filter(self, tag_id: str) -> None:
        self._keys_proxy.set_tag_filter(tag_id)
        self._sync_list()

    def _selected_key(self) -> SshKey | None:
        indexes = self._keys_table.selectionModel().selectedRows()
        if not indexes:
            return None
        source_index = self._keys_proxy.mapToSource(indexes[0])
        return self._keys_model.key_at(source_index.row())

    def refresh_keys(self) -> None:
        selected = self._selected_key()
        selected_name = selected.name if selected else ""
        self.statusBar().showMessage("Lecture des clés…")
        def completed(keys):
            self._keys_model.update_keys(keys)
            if self._tag_page:
                self._tag_page.set_keys(keys)
            self._tag_filter.rebuild()
            count = len(keys)
            self._sync_list()
            self._alert_nav.setText(f"À vérifier ({sum(bool(k.warning) for k in keys)})" if any(k.warning for k in keys) else "À vérifier")
            for row in range(self._keys_proxy.rowCount()):
                index = self._keys_proxy.index(row, 1)
                if index.data() == selected_name:
                    self._keys_table.selectRow(row)
                    break
            alerts = sum(bool(key.warning) for key in keys)
            message = f"{count} clés · {alerts} à vérifier" if alerts else ("Aucune clé. Créez ou importez votre première clé." if not count else "Liste actualisée")
            if metadata_store.LAST_WARNING:
                message += " · " + metadata_store.LAST_WARNING
                metadata_store.LAST_WARNING = ""
            self.statusBar().showMessage(message, 12000)
        self.run_task(ssh_manager.scan_keys, completed)

    def _on_new_key(self) -> None:
        if KeyCreateDialog(self).exec() == QDialog.DialogCode.Accepted:
            self.refresh_keys()
            self.statusBar().showMessage("Clé créée avec succès", 3000)

    def _on_open_ssh_folder(self) -> None:
        try:
            ssh_manager.open_ssh_folder()
        except OSError as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible d'ouvrir le dossier : {exc}")

    def _on_copy_public(self) -> None:
        key = self._selected_key()
        if not key:
            self.statusBar().showMessage("Sélectionnez une clé d'abord", 2500)
            return
        text, err = ssh_manager.read_public_key(key.name)
        if err:
            QMessageBox.warning(self, "Erreur", err)
            return
        QGuiApplication.clipboard().setText(text)
        self.statusBar().showMessage(f"Clé publique « {key.name} » copiée", 3000)

    def _on_key_double_click(self, index) -> None:
        source_index = self._keys_proxy.mapToSource(index)
        key = self._keys_model.key_at(source_index.row())
        if not key:
            return
        result = KeyDetailDialog(key, self).exec()
        if result in (QDialog.DialogCode.Accepted, 2):
            self.refresh_keys()

    def _on_import(self):
        source, _ = QFileDialog.getOpenFileName(self, "Importer une clé privée OpenSSH ou PEM", str(ssh_manager.SSH_DIR), "Tous les fichiers (*)")
        if not source:
            return
        name, accepted = QInputDialog.getText(self, "Nom de la clé", "Nom local", text=Path(source).stem.replace(".", "_"))
        if not accepted:
            return
        def completed(result):
            ok, error = result
            if ok:
                self.refresh_keys()
            elif "passphrase" in error.lower():
                password, accepted = QInputDialog.getText(self, "Clé chiffrée", "Passphrase de la clé importée", QLineEdit.EchoMode.Password)
                if accepted:
                    self.run_task(lambda: ssh_manager.import_key(Path(source), name.strip(), password), completed)
            else:
                QMessageBox.warning(self, "Import impossible", error)
        self.run_task(lambda: ssh_manager.import_key(Path(source), name.strip()), completed)

    def _on_restore(self):
        def listed(items):
            if TrashDialog(items, self).exec() == QDialog.DialogCode.Accepted:
                self.refresh_keys()
        self.run_task(ssh_manager.list_deleted_keys, listed)

    def _operation_finished(self, result):
        ok, error = result
        if ok:
            self.refresh_keys()
        else:
            QMessageBox.warning(self, "Opération impossible", error)

    def _on_agent(self):
        def completed(result):
            text, error = result
            AgentDialog(text, error, self).exec()
        self.run_task(ssh_manager.agent_keys, completed)

    def _on_manage_tags(self):
        try:
            if self._tag_page is None:
                self._tag_page = TagPage()
                self._tag_page.changed.connect(self.refresh_keys)
                self._pages.addWidget(self._tag_page)
            else:
                self._tag_page.refresh()
            self._tag_page.set_keys(self._keys_model._keys)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Tags", str(exc))
            self._tags_nav.setChecked(False)
            return
        self._pages.setCurrentWidget(self._tag_page)
        self._all_nav.setChecked(False)
        self._alert_nav.setChecked(False)
        self._tags_nav.setChecked(True)

    def closeEvent(self, event):
        if getattr(self, "_task", None) is None:
            QSettings().setValue("window/geometry", self.saveGeometry())
        super().closeEvent(event)
