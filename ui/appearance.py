"""Apparence Qt et intégration native Windows, sans installation de police."""
import ctypes
import os
import sys

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from ui.assets import FONT_PATH
from ui.theme import ACCENT, FONT_FAMILY, PANEL, SELECTED, TEXT, WINDOW


def prepare_text_rendering() -> None:
    """À appeler avant QApplication : rendu net de la police variable sous Windows."""
    if sys.platform == "win32":
        # Le moteur Windows conserve des franges ClearType malgré NoSubpixelAntialias.
        # FreeType respecte le lissage gris et la police Inter, y compris à DPI fractionnaire.
        # Un choix explicite de plateforme (tests offscreen, etc.) reste prioritaire.
        os.environ.setdefault("QT_QPA_PLATFORM", "windows:fontengine=freetype")


def apply_dark_palette(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    for role, value in (
        (QPalette.ColorRole.Window, WINDOW), (QPalette.ColorRole.WindowText, TEXT),
        (QPalette.ColorRole.Base, PANEL), (QPalette.ColorRole.AlternateBase, "#25252B"),
        (QPalette.ColorRole.Text, TEXT), (QPalette.ColorRole.Button, "#26262C"),
        (QPalette.ColorRole.ButtonText, TEXT), (QPalette.ColorRole.Highlight, SELECTED),
        (QPalette.ColorRole.HighlightedText, TEXT),
        (QPalette.ColorRole.PlaceholderText, "#868693"), (QPalette.ColorRole.Link, ACCENT),
        (QPalette.ColorRole.Light, "#48484E"), (QPalette.ColorRole.Mid, "#333338"),
        (QPalette.ColorRole.Dark, "#151517"), (QPalette.ColorRole.Shadow, "#101012"),
        (QPalette.ColorRole.ToolTipBase, "#333039"), (QPalette.ColorRole.ToolTipText, TEXT),
    ):
        palette.setColor(role, QColor(value))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#777783"))
    app.setPalette(palette)


def load_app_font(app: QApplication) -> bool:
    font_id = QFontDatabase.addApplicationFont(str(FONT_PATH))
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    font = QFont(FONT_FAMILY if FONT_FAMILY in families else "Segoe UI")
    font.setPixelSize(13)
    smooth_text_font(font)
    app.setFont(font)
    return FONT_FAMILY in families


def smooth_text_font(font: QFont) -> None:
    """Lissage en niveaux de gris, sans franges ClearType sur le fond sombre."""
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.NoSubpixelAntialias)
    font.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)


class NativeDarkWindows(QObject):
    """Colore aussi les barres de titre des fenêtres Qt sur Windows 11."""

    def eventFilter(self, watched, event):
        if (event.type() == QEvent.Type.Show and isinstance(watched, QWidget)
                and watched.isWindow() and sys.platform == "win32"
                and QApplication.platformName() == "windows"):
            self._apply(watched)
        return False

    @staticmethod
    def _apply(window):
        try:
            setter = ctypes.windll.dwmapi.DwmSetWindowAttribute
            setter.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
            setter.restype = ctypes.c_long
            handle = ctypes.c_void_p(int(window.winId()))
            enabled = ctypes.c_int(1)
            dark_result = setter(handle, 20, ctypes.byref(enabled), ctypes.sizeof(enabled))
            caption = ctypes.c_uint(0x00000000)  # COLORREF : 0x00BBGGRR.
            caption_result = setter(handle, 35, ctypes.byref(caption), ctypes.sizeof(caption))
            text = ctypes.c_uint(0x00F7F5F5)
            text_result = setter(handle, 36, ctypes.byref(text), ctypes.sizeof(text))
            return dark_result == caption_result == text_result == 0
        except (AttributeError, OSError):
            return False


def configure_appearance(app: QApplication) -> bool:
    apply_dark_palette(app)
    loaded = load_app_font(app)
    native_style = NativeDarkWindows(app)
    app.installEventFilter(native_style)
    app._harpie_native_style = native_style
    if sys.platform == "win32":
        try:
            setter = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
            setter.argtypes = [ctypes.c_wchar_p]
            setter.restype = ctypes.c_long
            setter("Harpie.SSHKeyManager")
        except (AttributeError, OSError):
            pass
    return loaded
