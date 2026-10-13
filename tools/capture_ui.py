"""Capture the real UI using disposable keys, never the user's SSH directory.

Run from the repository root: python tools/capture_ui.py
"""
import os
from pathlib import Path
import sys
import tempfile
import time
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def main():
    with tempfile.TemporaryDirectory(prefix="harpie-review-", dir=ROOT) as sandbox:
        os.environ["HARPIE_HOME"] = sandbox
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication
        from core import metadata_store as metadata, ssh_manager as ssh
        from ui.appearance import configure_appearance
        from ui.theme import APP_STYLESHEET
        from ui.main_window import MainWindow
        from ui.key_create_dialog import KeyCreateDialog
        from ui.key_detail_dialog import KeyDetailDialog
        from ui.tools_dialog import AgentDialog, TrashDialog

        app = QApplication([])
        app.setApplicationName("Harpie UI Preview")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, sandbox)
        configure_appearance(app)
        app.setStyleSheet(APP_STYLESHEET)
        tags = {name: metadata.create_tag(name, color) for name, color in
                (("Production", "#2197FE"), ("Personnel", "#A58AFF"), ("GitHub", "#EF89AD"))}
        fixtures = [
            ("atlas_production", "Infrastructure · serveur principal", "Production", "preview-only", "ed25519"),
            ("github_personal", "Dépôts et projets personnels", "GitHub", "preview-only", "ed25519"),
            ("homelab", "Serveur local · réseau personnel", "Personnel", "", "ed25519"),
            ("legacy_backup", "Sauvegardes · identité RSA", "Production", "", "rsa"),
            ("studio_deploy", "Déploiement · environnement de test", "Production", "preview-only", "ed25519"),
            ("travel_laptop", "Accès depuis le portable", "Personnel", "", "ed25519"),
        ]
        for index, (name, comment, tag, password, kind) in enumerate(fixtures):
            ok, error = ssh.create_key(name, comment, password, kind)
            if not ok:
                raise RuntimeError(error)
            metadata.set_key_tag(name, tags[tag])
            stamp = datetime(2026, 10, 12 - index, 10, 30).timestamp()
            for path in (ssh.SSH_DIR / name, ssh.SSH_DIR / (name + '.pub')):
                os.utime(path, (stamp, stamp))
        # Include a real missing-public-key warning in the screenshot.
        (ssh.SSH_DIR / 'travel_laptop.pub').unlink()
        window = MainWindow()
        deadline = time.monotonic() + 15
        while window._task and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.01)
        if window._task:
            raise RuntimeError("UI refresh timed out")
        output = ROOT / 'docs' / 'screenshots'
        output.mkdir(parents=True, exist_ok=True)
        review = ROOT / '.review'
        review.mkdir(exist_ok=True)

        def capture(widget, name, directory=output):
            widget.show()
            app.processEvents()
            if not widget.grab().save(str(directory / name)):
                raise RuntimeError(f"Could not save {name}")

        window.resize(1380, 980)
        capture(window, 'library.png')
        create = KeyCreateDialog(window)
        create._name.setText('new_identity')
        create._comment.setText('Un nouvel accès pour votre prochain projet')
        capture(create, 'create-key.png')
        create.close()
        detail = KeyDetailDialog(ssh.scan_keys()[0], window)
        capture(detail, 'key-details.png', review)
        for index in (1, 2):
            detail._tabs.setCurrentIndex(index)
            capture(detail, f'details-tab-{index}.png', review)
        detail.close()
        window._on_manage_tags()
        capture(window, 'tags.png')
        window._set_view(False)
        for width, height in ((920, 640), (1150, 760), (1280, 800)):
            window.resize(width, height)
            capture(window, f'library-{width}.png', review)
        trash = TrashDialog([{'name': 'retired_server', 'id': 'preview', 'deleted_at': '2026-10-10T16:45:00'}], window)
        capture(trash, 'trash.png', review)
        trash.close()
        agent = AgentDialog('256 SHA256:example agent identity (ED25519)', '', window)
        capture(agent, 'agent.png', review)
        agent.close()
        window._search.setText('no-match')
        capture(window, 'filtered-empty.png', review)
        window._search.clear()
        window._keys_model.update_keys([])
        capture(window, 'empty-library.png', review)
        window.close()
        app.processEvents()
        print(f"UI screenshots saved to {output}")


if __name__ == '__main__':
    main()
