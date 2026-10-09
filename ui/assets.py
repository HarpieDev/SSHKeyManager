from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
FONT_PATH = ASSETS_DIR / "fonts" / "InterVariable.ttf"
LOGO_SVG = ICONS_DIR / "harpie.svg"
REFRESH_SVG = ICONS_DIR / "refresh.svg"


def logo_path() -> Path:
    return LOGO_SVG


def refresh_icon_path() -> Path:
    return REFRESH_SVG
