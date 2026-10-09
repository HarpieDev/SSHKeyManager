"""Harpie : noir profond, cartes arrondies et capsules inspirées des références Apple."""
from ui.assets import ICONS_DIR

FONT_FAMILY = "Inter Variable"
WINDOW = "#000000"
PANEL = "#1C1C1E"
HOVER = "#272729"
SELECTED = "#17364B"
TEXT = "#F5F5F7"
SECONDARY = "#98989F"
MUTED = "#85858D"
BORDER = "#323236"
ACCENT = "#2197FE"
WARNING = "#E9A76C"
# Couleurs relevées dans les captures Display P3, puis converties en sRGB.
BLUE = "#2197FE"
PURPLE = "#8453BF"
PINK = "#EF89AD"
ORANGE = "#E9A76C"
GRAY = "#9DA5AA"

APP_STYLESHEET = '''
QWidget { font-family: "@FONT@"; font-size: 13px; color: #F5F5F7; }
QMainWindow, QDialog { background: #000000; }
QMainWindow#HarpieWindow, QWidget#WindowCanvas, QWidget#WindowTitleBar { background: #202020; }
QFrame#AppSurface { background: #000000; border: none; border-radius: 18px; }
QMainWindow#HarpieWindow QStatusBar { background: #202020; }
QPushButton#WindowControl, QPushButton#WindowClose { background: transparent; border: none; border-radius: 6px; padding: 0; min-height: 0; min-width: 0; }
QPushButton#WindowControl:hover { background: #38383A; }
QPushButton#WindowControl:pressed { background: #242426; }
QPushButton#WindowClose:hover { background: #C42B36; }
QPushButton#WindowClose:pressed { background: #A9232C; }
QPushButton#WindowControl:focus[keyboardFocus="true"], QPushButton#WindowClose:focus[keyboardFocus="true"] { border: 1px solid #2197FE; }
QLabel { background: transparent; }
QLabel#AppTitle { font-size: 38px; font-weight: 700; color: #F5F5F7; }
QLabel#AppSubtitle { color: #98989F; font-size: 13px; }
QLabel#SectionTitle { font-size: 19px; font-weight: 600; color: #F5F5F7; }
QLabel#FieldLabel { font-size: 13px; font-weight: 500; color: #D4D4D9; }
QLabel#Eyebrow { font-size: 11px; font-weight: 500; color: #98989F; }
QLabel#SidebarSection { font-size: 12px; font-weight: 600; color: #85858D; padding: 0 10px; }
QLabel#FooterNote { color: #85858D; font-size: 11px; }
QLabel#StatBadge { background: #2C2C2E; color: #AEAEB2; border-radius: 11px; padding: 4px 11px; font-size: 12px; }
QFrame#Card, QFrame#PreviewCard { background: #1C1C1E; border: none; border-radius: 26px; }
QLabel#PreviewTitle { font-size: 20px; font-weight: 600; color: #F5F5F7; }
QLabel#PreviewSymbol { background: #14364B; border-radius: 14px; }
QLabel#ConnectionTitle, QLabel#ProtectionTitle, QLabel#SecurityTitle { font-size: 19px; font-weight: 600; }
QLabel#ConnectionTitle { color: #2197FE; }
QLabel#ProtectionTitle { color: #B88AE9; }
QLabel#SecurityTitle { color: #EF89AD; }
QLabel#DetailCaption { font-size: 11px; color: #98989F; }
QLabel#DetailValue { font-size: 13px; color: #E5E5EA; }
QFrame#SummaryCard { background: #1C1C1E; border: none; border-radius: 24px; }
QFrame#SummaryCard[tone="blue"] { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6DBBEE, stop:1 #4A9BE2); }
QFrame#SummaryCard[tone="purple"] { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #8453BF, stop:1 #7745B2); }
QFrame#SummaryCard[tone="orange"] { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #F3C28E, stop:1 #E9A76C); }
QLabel#SummaryIcon { background: rgba(255, 255, 255, 35); border-radius: 16px; }
QLabel#SummaryValue { font-size: 32px; font-weight: 600; color: #FFFFFF; }
QLabel#SummaryTitle { font-size: 14px; font-weight: 600; color: #F5F5F7; }
QLabel#SummaryHint { font-size: 11px; color: #98989F; }
QFrame#SummaryCard[tone="purple"] QLabel#SummaryHint { color: #EEE1FF; }
QFrame#SummaryCard[tone="blue"] QLabel#SummaryValue, QFrame#SummaryCard[tone="blue"] QLabel#SummaryTitle { color: #102C46; }
QFrame#SummaryCard[tone="blue"] QLabel#SummaryHint { color: #183D56; }
QFrame#SummaryCard[tone="orange"] QLabel#SummaryValue, QFrame#SummaryCard[tone="orange"] QLabel#SummaryTitle { color: #3A240F; }
QFrame#SummaryCard[tone="orange"] QLabel#SummaryHint { color: #513317; }
QFrame#Sidebar { background: #121214; border: none; border-top-left-radius: 18px; border-bottom-left-radius: 18px; }
QFrame#Sidebar QLabel#Brand { color: #F5F5F7; font-size: 24px; font-weight: 600; }
QFrame#Sidebar QPushButton { text-align: left; background: transparent; border: 1px solid transparent; color: #C2C2CA; padding: 12px; border-radius: 16px; font-size: 13px; }
QFrame#Sidebar QPushButton:hover { background: #242426; color: #FFFFFF; }
QFrame#Sidebar QPushButton:checked { background: #17364B; color: #93CFFF; font-weight: 500; }
QFrame#Sidebar QPushButton#WarningNav:checked { background: #3B2B1C; color: #F3C28E; }
QFrame#Sidebar QPushButton#TagsNav:checked { background: #352745; color: #D0AFF4; }
QListWidget#TagList { background: #1C1C1E; border: none; outline: none; }
QFrame#TagNotice { background: #2B2328; border: 1px solid #50353E; border-radius: 18px; }
QLabel#TagError { color: #EF89AD; font-size: 13px; }
QFrame#RoundedPopup { background: transparent; border: none; }
QFrame#ComboPopupPanel { background: #2C2C2E; border: 1px solid #48484A; border-radius: 18px; }
QListWidget#ComboPopupList { background: transparent; border: none; outline: none; padding: 0; }
QListWidget#ComboPopupList::item { color: #D1D1D6; border: none; border-radius: 12px; padding: 8px 10px; }
QListWidget#ComboPopupList::item:hover { background: #38383A; }
QListWidget#ComboPopupList::item:selected { background: #17364B; color: #F5F5F7; }
QPushButton, QToolButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #363639, stop:1 #29292C); color: #F5F5F7; border: 1px solid #46464A; border-radius: 21px; padding: 9px 16px; min-height: 22px; font-weight: 500; }
QPushButton:hover, QToolButton:hover { background: #3D3D41; border-color: #5A5A61; }
QPushButton:pressed, QToolButton:pressed { background: #242426; }
QPushButton:focus, QToolButton:focus { border-color: #2197FE; }
QPushButton#PrimaryBtn { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2197FE, stop:1 #0D88FE); color: #FFFFFF; border: 1px solid #429FFF; }
QPushButton#PrimaryBtn:hover { background: #35A3FF; border-color: #79C3FF; }
QPushButton#PrimaryBtn:pressed { background: #0074DC; }
QPushButton#TintedBtn { background: #12364B; border: 1px solid #214B64; color: #59B4FF; }
QPushButton#TintedBtn:hover { background: #194B69; border-color: #34769A; }
QPushButton#DangerBtn { color: #EF89AD; border-color: #5A3341; background: #38222B; }
QPushButton#DangerBtn:hover { background: #4A2B39; border-color: #96536B; }
QPushButton#GhostDangerBtn { background: transparent; border-color: transparent; color: #EF89AD; }
QPushButton#GhostDangerBtn:hover { background: #38222B; border-color: #5A3341; }
QPushButton#GhostBtn { background: transparent; border-color: transparent; color: #2197FE; }
QPushButton:disabled, QToolButton:disabled { color: #75757F; background: #242426; border-color: #303034; }
QPushButton#PrimaryBtn:disabled { color: #81929F; background: #1C2F3D; border-color: #2B414F; }
QFrame#GlassToolbar { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #303033, stop:1 #202022); border: 1px solid #454549; border-radius: 22px; }
QPushButton#ToolbarBtn { background: transparent; border: 1px solid transparent; border-radius: 18px; padding: 8px 12px; min-height: 20px; }
QPushButton#ToolbarBtn:hover { background: #3B3B3F; }
QLineEdit, QComboBox, QSpinBox { background: #2C2C2E; border: 1px solid transparent; border-radius: 15px; padding: 10px 13px; selection-background-color: #175F91; selection-color: #FFFFFF; color: #F5F5F7; min-height: 18px; }
QLineEdit:hover, QComboBox:hover, QSpinBox:hover { border-color: #48484D; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: #2197FE; background: #242F38; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled { background: #232325; color: #72727F; }
QLineEdit#SearchField { background: #1C1C1E; border-radius: 24px; padding: 10px 14px; min-height: 26px; font-size: 14px; }
QLineEdit#SearchField:focus { border-color: #2197FE; }
QLineEdit QToolButton { background: transparent; border: none; border-radius: 0; padding: 0; min-height: 0; min-width: 0; }
QLineEdit QToolButton:hover { background: transparent; }
QComboBox { padding-right: 28px; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView { background: #2C2C2E; border: 1px solid #48484D; padding: 8px; selection-background-color: #17364B; selection-color: #F5F5F7; outline: none; }
QSpinBox { padding-right: 25px; }
QSpinBox::up-button, QSpinBox::down-button { width: 22px; border: none; background: #343437; }
QTextEdit { background: #262629; color: #D1D1D6; border: 1px solid transparent; border-radius: 16px; padding: 12px; font-family: Consolas; font-size: 12px; selection-background-color: #175F91; selection-color: #FFFFFF; }
QTableView { background: #1C1C1E; color: #F5F5F7; border: none; selection-background-color: #17364B; selection-color: #F5F5F7; outline: none; }
QTableView::item { padding: 10px; border: none; border-bottom: 1px solid #323236; }
QTableView::item:selected { background: #17364B; }
QTableView::item:hover { background: #272729; }
QHeaderView::section { background: #1C1C1E; color: #98989F; font-size: 11px; font-weight: 500; padding: 9px 10px; border: none; border-bottom: 1px solid #323236; }
QHeaderView { background: #1C1C1E; }
QStatusBar { background: #000000; color: #85858D; font-size: 11px; border: none; padding: 2px 16px; }
QStatusBar::item { border: none; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 4px 0; }
QScrollBar::handle:vertical { background: #48484A; border-radius: 4px; min-height: 30px; }
QScrollBar:horizontal { background: transparent; height: 8px; margin: 0 4px; }
QScrollBar::handle:horizontal { background: #48484A; border-radius: 4px; min-width: 30px; }
QScrollBar::handle:hover { background: #7D868C; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QTabWidget::pane { background: #1C1C1E; border: none; border-radius: 24px; top: 10px; }
QTabBar { background: #1C1C1E; border-radius: 19px; }
QTabBar::tab { background: transparent; color: #98989F; padding: 10px 16px; border: 1px solid transparent; border-radius: 16px; margin: 3px; }
QTabBar::tab:selected { background: #414145; color: #F5F5F7; border-color: #505055; font-weight: 500; }
QTabBar::tab:hover { color: #F5F5F7; background: #2C2C30; }
QCheckBox { spacing: 8px; color: #D1D1D6; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #636366; border-radius: 4px; background: #2C2C2E; }
QCheckBox::indicator:checked { background: #2197FE; border-color: #6DBBEE; }
QMenu { background: #2C2C2E; color: #F5F5F7; border: 1px solid #48484A; padding: 8px; border-radius: 16px; }
QMenu::item { padding: 10px 20px; border-radius: 9px; }
QMenu::item:selected { background: #17364B; }
QMenu::separator { height: 1px; background: #38383A; margin: 4px 10px; }
QToolTip { background: #2C2C2E; color: #F5F5F7; border: 1px solid #48484A; border-radius: 5px; padding: 6px; }
QMessageBox { background: #1C1C1E; }
QDialogButtonBox QPushButton { min-width: 82px; }
'''.replace("@FONT@", FONT_FAMILY)

APP_STYLESHEET += f'''
QComboBox::down-arrow {{ image: url("{(ICONS_DIR / 'chevron-down.svg').as_posix()}"); width: 14px; height: 14px; }}
QSpinBox::up-arrow {{ image: url("{(ICONS_DIR / 'chevron-up.svg').as_posix()}"); width: 12px; height: 12px; }}
QSpinBox::down-arrow {{ image: url("{(ICONS_DIR / 'chevron-down.svg').as_posix()}"); width: 12px; height: 12px; }}
'''

COLOR_PALETTE = [
    "#EE9193", "#E9A76C", "#FFCC00", "#D1D84B", "#30D158",
    "#72AE8C", "#30D6CB", "#32D2F0", "#6DBBEE", "#2197FE",
    "#696DFF", "#8453BF", "#A58AFF", "#BF5AF2", "#EF89AD",
    "#E26389", "#FF453A", "#9DA5AA", "#7D868C", "#636366",
]


def chip_colors(hex_color: str) -> tuple[str, str, str]:
    """Une couleur de tag reste lisible sur les surfaces sombres."""
    from PySide6.QtGui import QColor
    base = QColor(hex_color)
    if not base.isValid():
        base = QColor("#8B7AB0")
    surface = QColor(PANEL)
    def blend(amount):
        return QColor(*(round(c * amount + s * (1 - amount)) for c, s in zip(
            (base.red(), base.green(), base.blue()), (surface.red(), surface.green(), surface.blue())))).name()
    foreground = QColor(*(round(c * .53 + 255 * .47) for c in (base.red(), base.green(), base.blue()))).name()
    return blend(.14), foreground, blend(.35)


def tag_display(label: str) -> str:
    return label or "—"
