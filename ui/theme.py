"""Shared visual tokens for Harpie's local SSH workspace."""
from ui.assets import ICONS_DIR

FONT_FAMILY = "Inter Variable"
WINDOW = "#0C0E12"
PANEL = "#15181E"
HOVER = "#1D222C"
SELECTED = "#1C2D44"
TEXT = "#F1F4FA"
SECONDARY = "#9BA5B7"
MUTED = "#7F899B"
BORDER = "#272D38"
ACCENT = BLUE = "#619FFF"
WARNING = ORANGE = "#F0B779"
PURPLE = "#AD93EB"
PINK = "#E896B4"
GRAY = "#9DA5AA"

APP_STYLESHEET = '''
QWidget { font-family: "@FONT@"; font-size: 13px; color: #F1F4FA; }
QMainWindow, QDialog { background: #0C0E12; }
QMainWindow#HarpieWindow, QWidget#WindowCanvas, QWidget#WindowTitleBar { background: #0C0E12; }
QFrame#AppSurface { background: #101218; border: 1px solid #272D38; border-radius: 18px; }
QPushButton#WindowControl, QPushButton#WindowClose { background: transparent; border: none; border-radius: 6px; padding: 0; min-height: 0; min-width: 0; }
QPushButton#WindowControl:hover { background: #252B35; }
QPushButton#WindowControl:pressed { background: #1B2029; }
QPushButton#WindowClose:hover { background: #C42B36; }
QPushButton#WindowClose:pressed { background: #A9232C; }
QPushButton#WindowControl:focus[keyboardFocus="true"], QPushButton#WindowClose:focus[keyboardFocus="true"] { border: 1px solid #619FFF; }
QLabel { background: transparent; }
QLabel#AppTitle { font-size: 34px; font-weight: 600; color: #F1F4FA; }
QLabel#AppSubtitle { color: #9BA5B7; font-size: 13px; }
QLabel#SectionTitle { font-size: 17px; font-weight: 600; color: #F1F4FA; }
QLabel#FieldLabel { font-size: 12px; font-weight: 500; color: #BBC4D3; }
QLabel#Eyebrow { font-size: 10px; font-weight: 600; color: #7F899B; letter-spacing: 2px; }
QLabel#SidebarSection { font-size: 10px; font-weight: 600; color: #7F899B; letter-spacing: 1px; padding: 0 12px; }
QLabel#FooterNote { color: #7F899B; font-size: 10px; }
QLabel#StatBadge { background: #232A35; color: #B4C1D7; border-radius: 10px; padding: 3px 9px; font-size: 11px; }
QLabel#LocalBadge { background: #152B25; color: #86C7AE; border: 1px solid #26463A; border-radius: 13px; padding: 5px 12px; font-size: 10px; font-weight: 500; }
QLabel#KeyboardHint { color: #7F899B; background: #191E27; border: 1px solid #303846; border-radius: 5px; padding: 3px 6px; font-size: 10px; }
QFrame#Card, QFrame#PreviewCard { background: #15181E; border: 1px solid #272D38; border-radius: 20px; }
QFrame#PreviewHero { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #20334F, stop:1 #1B2030); border: 1px solid #334761; border-radius: 16px; }
QLabel#PreviewTitle { font-size: 20px; font-weight: 600; color: #F1F4FA; }
QLabel#PreviewSymbol { background: #263C5B; border: 1px solid #3A5375; border-radius: 14px; }
QLabel#PreviewState { color: #B6C8E3; font-size: 12px; }
QFrame#Rule { background: #272D38; border: none; min-height: 1px; max-height: 1px; }
QLabel#ConnectionTitle, QLabel#ProtectionTitle, QLabel#SecurityTitle { font-size: 17px; font-weight: 600; }
QLabel#ConnectionTitle { color: #81B3FF; }
QLabel#ProtectionTitle { color: #AD93EB; }
QLabel#SecurityTitle { color: #E896B4; }
QLabel#DetailCaption { font-size: 11px; color: #7F899B; }
QLabel#DetailValue { font-size: 13px; color: #DCE3EF; }
QLabel#Fingerprint { font-family: Consolas; font-size: 11px; color: #B4C1D7; background: #101319; border: 1px solid #272D38; padding: 12px; border-radius: 10px; }
QLabel#SecurityNote { background: #17231F; border: 1px solid #283C33; color: #91B9A8; padding: 12px; border-radius: 12px; font-size: 11px; }
QFrame#SummaryCard { background: #15181E; border: 1px solid #272D38; border-radius: 16px; }
QLabel#SummaryIcon { border-radius: 12px; }
QFrame#SummaryCard[tone="blue"] QLabel#SummaryIcon { background: #1C304A; }
QFrame#SummaryCard[tone="purple"] QLabel#SummaryIcon { background: #2D263F; }
QFrame#SummaryCard[tone="orange"] QLabel#SummaryIcon { background: #372B22; }
QLabel#SummaryValue { font-size: 30px; font-weight: 600; color: #F1F4FA; }
QLabel#SummaryTitle { font-size: 12px; font-weight: 500; color: #C4CDDB; }
QLabel#SummaryHint { font-size: 10px; color: #7F899B; }
QFrame#Sidebar { background: #11141A; border: none; border-right: 1px solid #272D38; border-top-left-radius: 18px; border-bottom-left-radius: 18px; }
QFrame#Sidebar QLabel#Brand { color: #F1F4FA; font-size: 23px; font-weight: 600; }
QFrame#Sidebar QPushButton { text-align: left; background: transparent; border: 1px solid transparent; color: #9BA5B7; padding: 9px 12px; border-radius: 12px; font-size: 12px; }
QFrame#Sidebar QPushButton:hover { background: #1C212B; color: #F1F4FA; }
QFrame#Sidebar QPushButton:checked { background: #1C2D44; border-color: #2F4563; color: #9CC6FF; font-weight: 500; }
QFrame#Sidebar QPushButton:focus { border-color: #619FFF; }
QFrame#Sidebar QPushButton#WarningNav:checked { background: #33291F; border-color: #4B3929; color: #F0B779; }
QFrame#Sidebar QPushButton#TagsNav:checked { background: #2B253A; border-color: #443657; color: #CBB4F8; }
QFrame#LocalCard { background: #181D25; border: 1px solid #2B3340; border-radius: 14px; }
QListWidget#TagList { background: #15181E; border: none; outline: none; }
QListWidget#TrashList { background: #15181E; border: 1px solid #272D38; border-radius: 14px; padding: 8px; outline: none; }
QListWidget#TrashList::item { padding: 14px; border-radius: 10px; margin: 2px; color: #BBC4D3; }
QListWidget#TrashList::item:selected { background: #1C2D44; color: #F1F4FA; }
QListWidget#TrashList::item:hover { background: #1D222C; }
QFrame#TagNotice { background: #2B222B; border: 1px solid #503541; border-radius: 14px; }
QLabel#TagError { color: #E896B4; font-size: 12px; }
QFrame#RoundedPopup { background: transparent; border: none; }
QFrame#ComboPopupPanel { background: #1D222C; border: 1px solid #3A4353; border-radius: 16px; }
QListWidget#ComboPopupList { background: transparent; border: none; outline: none; padding: 0; }
QListWidget#ComboPopupList::item { color: #DCE3EF; border: none; border-radius: 10px; padding: 8px 10px; }
QListWidget#ComboPopupList::item:hover { background: #2A3342; }
QListWidget#ComboPopupList::item:selected { background: #1C2D44; color: #F1F4FA; }
QPushButton, QToolButton { background: #222833; color: #DCE3EF; border: 1px solid #364051; border-radius: 20px; padding: 8px 15px; min-height: 22px; font-weight: 500; }
QPushButton:hover, QToolButton:hover { background: #2C3543; border-color: #50617B; }
QPushButton:pressed, QToolButton:pressed { background: #1B2029; }
QPushButton:focus, QToolButton:focus { border-color: #619FFF; }
QPushButton#PrimaryBtn { background: #538EF3; color: #FFFFFF; border: 1px solid #76ACFF; }
QPushButton#PrimaryBtn:hover { background: #689FF8; border-color: #A2C9FF; }
QPushButton#PrimaryBtn:pressed { background: #4078D4; }
QPushButton#TintedBtn { background: #1C2D44; border: 1px solid #344F73; color: #9CC6FF; }
QPushButton#TintedBtn:hover { background: #263E5D; border-color: #567BAC; }
QPushButton#DangerBtn { color: #E896B4; border-color: #583849; background: #34232D; }
QPushButton#DangerBtn:hover { background: #482C3A; border-color: #8B526E; }
QPushButton#GhostDangerBtn { background: transparent; border-color: transparent; color: #E896B4; }
QPushButton#GhostDangerBtn:hover { background: #34232D; border-color: #583849; }
QPushButton#GhostBtn { background: transparent; border-color: transparent; color: #9CC6FF; }
QPushButton#FilterChip { background: transparent; border: 1px solid #303846; border-radius: 15px; color: #9BA5B7; padding: 3px 11px; min-height: 22px; font-size: 11px; }
QPushButton#FilterChip:hover { background: #202735; }
QPushButton#FilterChip:checked { background: #263C5B; border-color: #3C5981; color: #B8D6FF; }
QPushButton:disabled, QToolButton:disabled { color: #687387; background: #1B2028; border-color: #272D38; }
QPushButton#PrimaryBtn:disabled { color: #7F92B0; background: #20334F; border-color: #2C4161; }
QFrame#GlassToolbar { background: #15181E; border: 1px solid #303846; border-radius: 22px; }
QPushButton#ToolbarBtn { background: transparent; border: 1px solid transparent; border-radius: 18px; padding: 8px 12px; min-height: 20px; }
QPushButton#ToolbarBtn:hover { background: #252D3A; }
QLineEdit, QComboBox, QSpinBox { background: #1D222C; border: 1px solid #303846; border-radius: 12px; padding: 10px 13px; selection-background-color: #355C90; selection-color: #FFFFFF; color: #F1F4FA; min-height: 18px; }
QLineEdit:hover, QComboBox:hover, QSpinBox:hover { border-color: #49566B; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: #619FFF; background: #1D2736; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled { background: #181C24; color: #687387; }
QLineEdit#SearchField { background: #15181E; border: 1px solid #303846; border-radius: 22px; padding: 10px 14px; min-height: 24px; font-size: 13px; }
QLineEdit QToolButton { background: transparent; border: none; border-radius: 0; padding: 0; min-height: 0; min-width: 0; }
QLineEdit QToolButton:hover { background: transparent; }
QComboBox { padding-right: 28px; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView { background: #1D222C; border: 1px solid #49566B; padding: 8px; selection-background-color: #1C2D44; selection-color: #F1F4FA; outline: none; }
QSpinBox { padding-right: 25px; }
QSpinBox::up-button, QSpinBox::down-button { width: 22px; border: none; background: #293140; }
QTextEdit { background: #101319; color: #B4C1D7; border: 1px solid #303846; border-radius: 12px; padding: 12px; font-family: Consolas; font-size: 12px; selection-background-color: #355C90; selection-color: #FFFFFF; }
QTableView { background: #15181E; color: #DCE3EF; border: none; selection-background-color: #1C2D44; selection-color: #F1F4FA; outline: none; }
QTableView::item { padding: 10px; border: none; border-bottom: 1px solid #272D38; font-size: 12px; }
QTableView::item:selected { background: #1C2D44; }
QTableView::item:hover { background: #1D222C; }
QHeaderView::section { background: #15181E; color: #7F899B; font-size: 10px; font-weight: 500; padding: 11px 10px; border: none; border-bottom: 1px solid #272D38; }
QHeaderView { background: #15181E; }
QStatusBar { background: #0C0E12; color: #7F899B; font-size: 10px; border: none; padding: 0 16px; }
QStatusBar::item { border: none; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 7px; margin: 4px 0; }
QScrollBar::handle:vertical { background: #364051; border-radius: 3px; min-height: 30px; }
QScrollBar:horizontal { background: transparent; height: 7px; margin: 0 4px; }
QScrollBar::handle:horizontal { background: #364051; border-radius: 3px; min-width: 30px; }
QScrollBar::handle:hover { background: #61728C; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QTabWidget::pane { background: #15181E; border: 1px solid #272D38; border-radius: 16px; top: 12px; }
QTabBar { background: #15181E; border-radius: 17px; }
QTabBar::tab { background: transparent; color: #9BA5B7; padding: 10px 14px; border: 1px solid transparent; border-radius: 14px; margin: 3px; font-size: 12px; }
QTabBar::tab:selected { background: #26344B; color: #B8D6FF; border-color: #3B4D6A; font-weight: 500; }
QTabBar::tab:hover { color: #F1F4FA; background: #222833; }
QCheckBox { spacing: 8px; color: #DCE3EF; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #61728C; border-radius: 4px; background: #1D222C; }
QCheckBox::indicator:checked { background: #619FFF; border-color: #9CC6FF; }
QMenu { background: #1D222C; color: #F1F4FA; border: 1px solid #49566B; padding: 8px; border-radius: 12px; }
QMenu::item { padding: 10px 20px; border-radius: 8px; }
QMenu::item:selected { background: #1C2D44; }
QMenu::separator { height: 1px; background: #303846; margin: 4px 10px; }
QToolTip { background: #222833; color: #F1F4FA; border: 1px solid #49566B; border-radius: 5px; padding: 6px; }
QMessageBox { background: #15181E; }
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
