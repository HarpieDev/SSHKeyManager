from core.i18n import tr
import sys
import os
import json
import argparse
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
from core import metadata_store, key_material, ssh_manager
from ui.assets import logo_path, ICONS_DIR
from ui.main_window import MainWindow
from ui.theme import APP_STYLESHEET
from ui.appearance import configure_appearance, prepare_text_rendering
from version import __version__
from ui.language import initialize_language, change_language
from core.i18n import language


def main() -> int:
    parser = argparse.ArgumentParser(description="Harpie SSH Key Manager")
    parser.add_argument('--self-check', action='store_true')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--language', choices=('en', 'fr'))
    options, qt_options = parser.parse_known_args()
    self_check = options.self_check
    if self_check and not os.environ.get("HARPIE_HOME"):
        return 2  # Le diagnostic ne doit jamais utiliser les vraies clés.
    debug = options.debug
    setup_logging(debug=debug)

    prepare_text_rendering()
    app = QApplication([sys.argv[0], *qt_options])
    app.setApplicationName("Harpie SSH Key Manager")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Harpie")
    if os.environ.get("HARPIE_HOME"):
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, os.environ["HARPIE_HOME"])

    initialize_language(options.language)
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
                QMessageBox.information(None, "Harpie", tr('Harpie est déjà ouvert, ou son dossier de données est inaccessible.'))
            return 1
        window = MainWindow()
    except (OSError, ValueError) as exc:
        if not self_check:
            QMessageBox.critical(None, tr('Démarrage impossible'), str(exc))
        return 1
    if self_check:
        app.setQuitOnLastWindowClosed(False)
        report = Path(os.environ["HARPIE_HOME"]) / "self-check.json"
        scenarios = [('en', 'ed25519', 'temporary diagnostic passphrase'), ('fr', 'rsa', '')]
        scenario = 0
        preferred = language()
        assets_ok = False

        def submit_creation():
            from PySide6.QtWidgets import QDialogButtonBox
            from ui.key_create_dialog import KeyCreateDialog
            dialog = app.activeModalWidget()
            if not isinstance(dialog, KeyCreateDialog):
                app.exit(1)
                return
            locale, kind, password = scenarios[scenario]
            dialog._name.setText('self_check_' + locale)
            dialog._type.setCurrentIndex(dialog._type.findData(kind))
            dialog._passphrase.setText(password)
            dialog._confirm.setText(password)
            dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()

        def create_next():
            change_language(scenarios[scenario][0], persist=False)
            QTimer.singleShot(25, submit_creation)
            window._on_new_key()
            QTimer.singleShot(0, verify_creation)

        def verify_creation():
            nonlocal scenario
            if getattr(window, "_task", None) is not None:
                QTimer.singleShot(50, verify_creation)
                return
            try:
                locale, kind, password = scenarios[scenario]
                assert window._keys_model.rowCount() == scenario + 1
                name = 'self_check_' + locale
                private = (ssh_manager.SSH_DIR / name).read_bytes()
                public = (ssh_manager.SSH_DIR / (name + '.pub')).read_bytes().strip()
                assert key_material.public_bytes(key_material.load_private(private, password)) == b" ".join(public.split(maxsplit=2)[:2])
                assert public.split(maxsplit=1)[0] == (b'ssh-ed25519' if kind == 'ed25519' else b'ssh-rsa')
                scenario += 1
                if scenario < len(scenarios):
                    create_next()
                    return
                # Remove only the disposable identities created by this diagnostic.
                for locale, _, _ in scenarios:
                    for suffix in ('', '.pub'):
                        (ssh_manager.SSH_DIR / ('self_check_' + locale + suffix)).unlink()
                change_language(preferred, persist=False)
                report.write_text(json.dumps({"startup": True, "encrypted_key": True, "key_creation": True, "assets": assets_ok, "font": font_loaded, "version": __version__, "languages": ["en", "fr"]}), encoding="utf-8")
                app.exit(0)
            except Exception:
                app.exit(1)

        def check():
            nonlocal assets_ok
            if getattr(window, "_task", None) is not None:
                QTimer.singleShot(50, check)
                return
            try:
                private, public = key_material.generate("ed25519", "diagnostic temporaire")
                assert key_material.public_bytes(key_material.load_private(private, "diagnostic temporaire")) == public
                assert not window._keys_model.rowCount()
                assets_ok = all((ICONS_DIR / name).is_file() for name in ("harpie.svg", "harpie.ico", "chevron-down.svg", "chevron-up.svg"))
                change_language('en', persist=False)
                assert window._all_nav.text() == 'All keys'
                change_language('fr', persist=False)
                assert window._all_nav.text() == 'Toutes les clés'
                create_next()
            except Exception:
                app.exit(1)
        QTimer.singleShot(0, check)
        QTimer.singleShot(20000, lambda: app.exit(1))
    else:
        window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
