import sys
import os
import json
from pathlib import Path

try:
    from PySide6.QtGui import QColor, QFont, QIcon, QPalette
    from PySide6.QtCore import QLockFile, QSettings, QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox
except ImportError as exc:
    if "--self-check" in sys.argv and os.environ.get("HARPIE_HOME"):
        report = Path(os.environ["HARPIE_HOME"]) / "self-check.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({"startup": False, "error": str(exc)}), encoding="utf-8")
        sys.exit(1)
    raise

from core.logger import setup_logging
from core import metadata_store, key_material
from ui.assets import logo_path, ICONS_DIR
from ui.main_window import MainWindow
from ui.theme import APP_STYLESHEET
from ui.appearance import configure_appearance, prepare_text_rendering
from version import __version__


def main() -> int:
    self_check = "--self-check" in sys.argv
    if self_check and not os.environ.get("HARPIE_HOME"):
        return 2  # Le diagnostic ne doit jamais utiliser les vraies clés.
    debug = "--debug" in sys.argv
    setup_logging(debug=debug)

    prepare_text_rendering()
    app = QApplication(sys.argv)
    app.setApplicationName("Harpie SSH Key Manager")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Harpie")
    if os.environ.get("HARPIE_HOME"):
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, os.environ["HARPIE_HOME"])

    font_loaded = configure_appearance(app)
    icon = QIcon(str(logo_path()))
    if not icon.isNull():
        app.setWindowIcon(icon)
    app.setStyleSheet(APP_STYLESHEET)

    try:
        metadata_store.METADATA_DIR.mkdir(parents=True, exist_ok=True)
        lock = QLockFile(str(metadata_store.METADATA_DIR / "harpie.lock"))
        lock.setStaleLockTime(0)
        if not lock.tryLock(0):
            if not self_check:
                QMessageBox.information(None, "Harpie", "Harpie est déjà ouvert, ou son dossier de données est inaccessible.")
            return 1
        window = MainWindow()
    except (OSError, ValueError) as exc:
        if not self_check:
            QMessageBox.critical(None, "Démarrage impossible", str(exc))
        return 1
    if self_check:
        report = Path(os.environ["HARPIE_HOME"]) / "self-check.json"
        def check():
            if getattr(window, "_task", None) is not None:
                QTimer.singleShot(50, check)
                return
            try:
                private, public = key_material.generate("ed25519", "diagnostic temporaire")
                assert key_material.public_bytes(key_material.load_private(private, "diagnostic temporaire")) == public
                assert not window._keys_model.rowCount()
                assets_ok = all((ICONS_DIR / name).is_file() for name in ("harpie.svg", "harpie.ico", "chevron-down.svg", "chevron-up.svg"))
                report.write_text(json.dumps({"startup": True, "encrypted_key": True, "assets": assets_ok, "font": font_loaded, "version": __version__}), encoding="utf-8")
                app.exit(0)
            except Exception:
                app.exit(1)
        QTimer.singleShot(0, check)
        QTimer.singleShot(20000, lambda: app.exit(1))
    else:
        window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
