"""Régressions sur des clés temporaires : jamais le vrai dossier .ssh."""
import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from core import key_material, metadata_store as m, ssh_manager as s
from core.storage import atomic_write, private_permission_warning

PROJECT = Path(__file__).resolve().parents[1]


class IsolatedTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="harpie-test-", dir=PROJECT)
        self.root = Path(self.temp.name).resolve()
        assert self.root.is_relative_to(PROJECT)
        self.previous = s.SSH_DIR, s.SSH_CONFIG, m.METADATA_DIR, m.METADATA_FILE
        s.SSH_DIR = self.root / "ssh"
        s.SSH_CONFIG = s.SSH_DIR / "config"
        m.METADATA_DIR = self.root / "metadata"
        m.METADATA_FILE = m.METADATA_DIR / "metadata.json"
        m.LAST_WARNING = ""
        s.get_ssh_dir()

    def tearDown(self):
        s.SSH_DIR, s.SSH_CONFIG, m.METADATA_DIR, m.METADATA_FILE = self.previous
        self.temp.cleanup()

    def create(self, name="demo", passphrase="", kind="ed25519"):
        ok, error = s.create_key(name, "VPS Dubai personnel", passphrase, kind)
        self.assertTrue(ok, error)
        return s.SSH_DIR / name


class KeyTests(IsolatedTest):
    def test_generation_scan_and_native_openssh(self):
        private = self.create()
        key = s.scan_keys()[0]
        self.assertEqual(key.comment, "VPS Dubai personnel")
        self.assertFalse(key.warning, key.warning)
        self.assertFalse(private_permission_warning(private))
        self.assertEqual(s._run("ssh-keygen", ["-y", "-f", str(private)]).stdout.strip(), " ".join(key.public_key_text.split()[:2]))
        self.assertIn(key.fingerprint_sha256, s._run("ssh-keygen", ["-l", "-E", "sha256", "-f", str(private) + ".pub"]).stdout)

    def test_encrypted_key_never_uses_a_process(self):
        with patch.object(subprocess, "run", side_effect=AssertionError("No secret in process")):
            private = self.create(passphrase="secret de test éè")
            self.assertTrue(s.scan_keys()[0].encrypted)
            self.assertTrue(s.update_comment("demo", "Commentaire complet avec espaces")[0])
        with self.assertRaises(ValueError):
            key_material.load_private(private.read_bytes(), "wrong")
        key_material.load_private(private.read_bytes(), "secret de test éè")

    def test_rsa4096(self):
        self.create(kind="rsa")
        self.assertEqual(s.scan_keys()[0].key_type, "ssh-rsa")
        self.assertIn("4096", s._run("ssh-keygen", ["-l", "-f", str(s.SSH_DIR / "demo.pub")]).stdout)

    def test_collision_even_without_public_and_case_insensitive(self):
        (s.SSH_DIR / "DEMO").write_text("unlisted", encoding="utf-8")
        self.assertFalse(s.create_key("demo", "", "")[0])
        self.assertEqual((s.SSH_DIR / "DEMO").read_text(), "unlisted")

    def test_reserved_names_and_traversal(self):
        for name in ("CON", "NUL", "config", "known_hosts", "COM1", "../escape", "a\nb"):
            self.assertFalse(s.create_key(name, "", "")[0], name)
        self.assertFalse(s.delete_key("../escape")[0])

    def test_orphan_key_and_repair(self):
        self.create(passphrase="secret")
        (s.SSH_DIR / "demo.pub").unlink()
        key = s.scan_keys()[0]
        self.assertIn(".pub manquant", key.warning)
        self.assertFalse(s.repair_public_key("demo")[0])
        self.assertTrue(s.repair_public_key("demo", "secret")[0])
        self.assertFalse(s.scan_keys()[0].warning)

    def test_public_only(self):
        self.create().unlink()
        key = s.scan_keys()[0]
        self.assertFalse(key.has_private)
        self.assertIn("privée manquante", key.warning)

    def test_mismatched_pair(self):
        self.create("one")
        self.create("two")
        (s.SSH_DIR / "one.pub").write_bytes((s.SSH_DIR / "two.pub").read_bytes())
        self.assertIn("ne correspondent pas", next(k for k in s.scan_keys() if k.name == "one").warning)

    def test_creation_rollback_when_public_write_fails(self):
        original = atomic_write
        def failing(path, *args, **kwargs):
            if path.suffix == ".pub":
                raise PermissionError("Locked")
            return original(path, *args, **kwargs)
        with patch.object(s, "atomic_write", side_effect=failing):
            self.assertFalse(s.create_key("demo", "", "")[0])
        self.assertFalse((s.SSH_DIR / "demo").exists())

    def test_comment_injection_rejected(self):
        self.assertFalse(s.create_key("demo", "line\nssh-rsa evil", "")[0])
        self.create()
        self.assertFalse(s.update_comment("demo", "line\nother")[0])

    def test_import_export_encrypted_and_existing_destination(self):
        private = self.create(passphrase="secret")
        self.assertFalse(s.import_key(private, "imported")[0])
        self.assertTrue(s.import_key(private, "imported", "secret")[0])
        destination = self.root / "exported"
        self.assertTrue(s.export_key("imported", destination, True)[0])
        self.assertEqual(private.read_bytes(), destination.read_bytes())
        self.assertFalse(private_permission_warning(destination))
        self.assertFalse(s.export_key("imported", destination, True)[0])

    def test_import_rejects_mismatched_companion(self):
        one = self.create("one")
        self.create("two")
        one.with_name("one.pub").write_bytes((s.SSH_DIR / "two.pub").read_bytes())
        self.assertFalse(s.import_key(one, "imported")[0])
        self.assertFalse((s.SSH_DIR / "imported").exists())

    def test_change_passphrase_preserves_identity_and_wrong_password_preserves_file(self):
        private = self.create(passphrase="old")
        fingerprint = s.scan_keys()[0].fingerprint_sha256
        before = private.read_bytes()
        self.assertFalse(s.change_passphrase("demo", "wrong", "new")[0])
        self.assertEqual(private.read_bytes(), before)
        self.assertTrue(s.change_passphrase("demo", "old", "new")[0])
        self.assertTrue(s.validate_key("demo", "new")[0])
        self.assertEqual(s.scan_keys()[0].fingerprint_sha256, fingerprint)
        self.assertTrue(s.change_passphrase("demo", "new", "")[0])
        self.assertFalse(s.scan_keys()[0].encrypted)

    def test_password_limit_and_invalid_private(self):
        self.assertFalse(s.create_key("demo", "", "a" * 73)[0])
        self.create()
        (s.SSH_DIR / "demo").write_bytes(b"-----BEGIN OPENSSH PRIVATE KEY-----\nbad\n-----END OPENSSH PRIVATE KEY-----\n")
        self.assertIn("privée illisible", s.scan_keys()[0].warning)


class ConfigTests(IsolatedTest):
    def test_prefix_delete_and_rename_all_exact_references(self):
        self.create("vps")
        content = 'Host prod\n IdentityFile ~/.ssh/vps_prod\nHost staging\n IdentityFile ~/.ssh/vps\nHost second\n IdentityFile "~/.ssh/vps" # comment\n'
        s.SSH_CONFIG.write_text(content, encoding="utf-8")
        self.assertTrue(s.rename_key("vps", "new_vps")[0])
        updated = s.SSH_CONFIG.read_text()
        self.assertIn("~/.ssh/vps_prod", updated)
        self.assertEqual(updated.count("~/.ssh/new_vps"), 2)
        self.assertIn('Host second', updated)
        self.assertIn('# comment', updated)
        self.assertTrue(s.delete_key("new_vps")[0])
        updated = s.SSH_CONFIG.read_text()
        self.assertIn("~/.ssh/vps_prod", updated)
        self.assertIn("Host staging", updated)
        self.assertNotIn("~/.ssh/new_vps", updated)

    def test_unindented_lowercase_equals_and_match(self):
        self.create()
        s.SSH_CONFIG.write_text('  host = demo\nhostname = old.example\nuser = old\nidentityfile = ~/.ssh/demo\nPort 2200\nProxyJump jump\n# keep\nMatch host other\nUser unrelated\n', encoding="utf-8")
        self.assertTrue(s.set_config_entry("demo", "new.example", "new", 2222)[0])
        content = s.SSH_CONFIG.read_text()
        self.assertNotIn("old.example", content)
        self.assertIn("ProxyJump jump", content)
        self.assertIn("# keep", content)
        self.assertIn("Match host other\nUser unrelated", content)
        self.assertEqual(s.get_config_entry("demo")["port"], "2222")

    def test_shared_alias_is_not_modified(self):
        self.create()
        content = "Host demo shared\n IdentityFile ~/.ssh/demo\n"
        s.SSH_CONFIG.write_text(content, encoding="utf-8")
        self.assertFalse(s.set_config_entry("demo", "test.example", "root")[0])
        self.assertEqual(s.SSH_CONFIG.read_text(), content)

    def test_defaults_precedence_with_native_parser(self):
        self.create()
        s.SSH_CONFIG.write_text("User fallback\nHost *\n Port 2200\n", encoding="utf-8")
        self.assertTrue(s.set_config_entry("demo", "192.0.2.1", "specific", 2222)[0])
        output = s._run("ssh", ["-G", "-F", str(s.SSH_CONFIG), "demo"]).stdout
        self.assertIn("user specific", output)
        self.assertIn("port 2222", output)
        self.assertTrue((s.SSH_DIR / "config.harpie.bak").exists())

    def test_config_injection(self):
        for host, user, port in (("test\nProxyCommand bad", "root", 22), ("test", "root\nUser evil", 22), ("test", "root", 0)):
            self.assertFalse(s.set_config_entry("demo", host, user, port)[0])
        self.assertFalse(s.SSH_CONFIG.exists())

    def test_partial_rename_rolls_back(self):
        self.create()
        original = Path.rename
        def failing(path, target):
            if path.name == "demo.pub":
                raise PermissionError("Locked")
            return original(path, target)
        with patch.object(Path, "rename", failing):
            self.assertFalse(s.rename_key("demo", "new")[0])
        self.assertTrue((s.SSH_DIR / "demo").exists())
        self.assertTrue((s.SSH_DIR / "demo.pub").exists())
        self.assertFalse((s.SSH_DIR / "new").exists())

    def test_config_write_failure_rolls_back_rename(self):
        self.create()
        self.assertTrue(s.set_config_entry("demo", "host.example", "root")[0])
        original = s.SSH_CONFIG.read_bytes()
        with patch.object(s, "_write_config", side_effect=PermissionError("Locked")):
            self.assertFalse(s.rename_key("demo", "new")[0])
        self.assertTrue((s.SSH_DIR / "demo").exists())
        self.assertEqual(s.SSH_CONFIG.read_bytes(), original)

    def test_delete_restore_and_collision(self):
        self.create()
        tag = m.create_tag("Personnel", "#3B82F6")
        m.set_key_tag("demo", tag)
        self.assertTrue(s.set_config_entry("demo", "server.example", "root")[0])
        config = s.SSH_CONFIG.read_bytes()
        original = (s.SSH_DIR / "demo").read_bytes()
        self.assertTrue(s.delete_key("demo")[0])
        self.assertFalse(s.scan_keys())
        archive = s.list_deleted_keys()[0]
        self.assertTrue(s.restore_deleted_key(archive["id"])[0])
        self.assertEqual((s.SSH_DIR / "demo").read_bytes(), original)
        self.assertEqual(s.SSH_CONFIG.read_bytes(), config)
        self.assertEqual(s.scan_keys()[0].tag_id, tag)
        self.assertFalse(s.list_deleted_keys())
        self.assertTrue(s.delete_key("demo")[0])
        archive = s.list_deleted_keys()[0]
        self.create()
        self.assertFalse(s.restore_deleted_key(archive["id"])[0])
        self.assertTrue(s.list_deleted_keys())

    def test_delete_failure_rolls_back(self):
        self.create()
        original = Path.rename
        def failing(path, target):
            if path.name == "demo.pub":
                raise PermissionError("Locked")
            return original(path, target)
        with patch.object(Path, "rename", failing):
            self.assertFalse(s.delete_key("demo")[0])
        self.assertTrue((s.SSH_DIR / "demo").exists())
        self.assertFalse(s.list_deleted_keys())

    def test_restore_preserves_subsequent_config_edits(self):
        self.create()
        self.assertTrue(s.set_config_entry("demo", "server.example", "root")[0])
        self.assertTrue(s.delete_key("demo")[0])
        s.SSH_CONFIG.write_text(s.SSH_CONFIG.read_text().replace("User root", "User updated") + "\nHost other\n User another\n ProxyJump jump\n", encoding="utf-8")
        archive = s.list_deleted_keys()[0]
        self.assertTrue(s.restore_deleted_key(archive["id"])[0])
        content = s.SSH_CONFIG.read_text()
        self.assertIn("User updated", content)
        self.assertIn("Host other", content)
        self.assertIn("ProxyJump jump", content)
        self.assertIn("IdentityFile ~/.ssh/demo", content)

    def test_alias_collision_preserves_existing_connection(self):
        content = "Host demo\n HostName production.example\n IdentityFile ~/.ssh/production\n"
        s.SSH_CONFIG.write_text(content, encoding="utf-8")
        self.assertFalse(s.set_config_entry("demo", "new.example", "root")[0])
        self.assertEqual(s.SSH_CONFIG.read_text(), content)

    def test_timeout_is_readable(self):
        with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("ssh-add", 15)):
            text, error = s.agent_keys()
        self.assertFalse(text)
        self.assertIn("15 secondes", error)


class MetadataTests(IsolatedTest):
    def test_tag_update_preserves_identity_and_associations_and_rejects_duplicates(self):
        tag = m.create_tag("Production", "#2197FE")
        m.create_tag("Personnel", "#8453BF")
        m.set_key_tag("demo", tag)
        m.update_tag(tag, "Serveurs", "#EF89AD")
        self.assertEqual(m.get_key_tag("demo"), (tag, "Serveurs", "#EF89AD"))
        before = m.METADATA_FILE.read_bytes()
        for tag_id, label, color in ((tag, "personnel", "#2197FE"), (tag, "", "#2197FE"),
                                     (tag, "Valid", "invalid"), ("missing", "Valid", "#2197FE")):
            with self.assertRaises(ValueError):
                m.update_tag(tag_id, label, color)
            self.assertEqual(m.METADATA_FILE.read_bytes(), before)
        with patch.object(m, "_save_raw", side_effect=PermissionError("Locked")):
            with self.assertRaises(PermissionError):
                m.update_tag(tag, "Unsaved", "#2197FE")
        self.assertEqual(m.METADATA_FILE.read_bytes(), before)

    def test_corrupt_metadata_is_backed_up(self):
        m.METADATA_DIR.mkdir()
        raw = b'{"version":2,"tags":null,"keys":{}}'
        m.METADATA_FILE.write_bytes(raw)
        self.assertEqual(m.list_tags(), [])
        backups = list(m.METADATA_DIR.glob("metadata.invalid-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), raw)
        self.assertTrue(m.LAST_WARNING)

    def test_duplicate_tags_and_concurrent_writes(self):
        m.create_tag("Personnel", "#3B82F6")
        with self.assertRaises(ValueError):
            m.create_tag("personnel", "#3B82F6")
        errors = []
        def create(index):
            try:
                m.create_tag(f"Tag {index}", "#3B82F6")
            except Exception as exc:
                errors.append(exc)
        threads = [threading.Thread(target=create, args=(i,)) for i in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertFalse(errors)
        self.assertEqual(len(m.list_tags()), 13)

    def test_legacy_tags_are_deduplicated(self):
        m.METADATA_DIR.mkdir()
        m.METADATA_FILE.write_text(json.dumps({"one": {"tag_id": "blue", "tag_label": "Perso"}, "two": {"tag_id": "blue", "tag_label": "Perso"}}))
        self.assertEqual(len(m.list_tags()), 1)
        self.assertEqual(m.get_key_tag("one"), m.get_key_tag("two"))

    def test_unknown_metadata_version_not_overwritten(self):
        m.METADATA_DIR.mkdir()
        raw = '{"version":99,"tags":{},"keys":{}}'
        m.METADATA_FILE.write_text(raw)
        with self.assertRaises(ValueError):
            m.list_tags()
        self.assertEqual(m.METADATA_FILE.read_text(), raw)

    def test_invalid_tag_reference_recovered(self):
        m.METADATA_DIR.mkdir()
        m.METADATA_FILE.write_text('{"version":2,"tags":{},"keys":{"demo":{"tag_id":[]}}}')
        self.assertEqual(m.list_tags(), [])


class UiTests(IsolatedTest):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        from ui.appearance import configure_appearance
        from ui.theme import APP_STYLESHEET
        cls.app = QApplication.instance() or QApplication([])
        assert configure_appearance(cls.app), "La police Inter intégrée doit être chargée."
        cls.app.setStyleSheet(APP_STYLESHEET)

    def test_trash_dialog_restores_identity_and_handles_empty_state(self):
        from PySide6.QtWidgets import QDialog
        from ui.tools_dialog import TrashDialog
        self.create('recover_me', passphrase='temporary secret')
        tag = m.create_tag('Recovery', '#2197FE')
        m.set_key_tag('recover_me', tag)
        private_before = (s.SSH_DIR / 'recover_me').read_bytes()
        self.assertTrue(s.delete_key('recover_me')[0])
        dialog = TrashDialog(s.list_deleted_keys())
        try:
            self.assertTrue(dialog._restore_btn.isEnabled())
            dialog._restore_btn.click()
            deadline = time.monotonic() + 10
            while getattr(dialog, '_task', None) and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(.01)
            self.assertIsNone(dialog._task)
            self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
            self.assertEqual((s.SSH_DIR / 'recover_me').read_bytes(), private_before)
            self.assertEqual(m.get_key_tag('recover_me')[0], tag)
        finally:
            dialog.deleteLater()
            self.app.processEvents()
        empty = TrashDialog(s.list_deleted_keys())
        try:
            self.assertFalse(empty._restore_btn.isEnabled())
            self.assertFalse(empty._empty.isHidden())
            empty._restore()
            self.assertIsNone(getattr(empty, '_task', None))
        finally:
            empty.deleteLater()
            self.app.processEvents()

    def test_integrated_window_controls_and_resize_zones(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        from ui.window_frame import IntegratedWindow
        window = IntegratedWindow()
        window.resize(1000, 700)
        window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        window.show()
        self.app.processEvents()
        try:
            self.assertTrue(window.windowFlags() & Qt.WindowType.FramelessWindowHint)
            self.assertEqual(window._hit_test(1, 1), 13)
            self.assertEqual(window._hit_test(999, 1), 14)
            self.assertEqual(window._hit_test(1, 699), 16)
            self.assertEqual(window._hit_test(999, 699), 17)
            self.assertEqual(window._hit_test(300, 15), 2)
            self.assertEqual(window._hit_test(950, 15), 1)
            self.assertEqual(window._hit_test(300, 200), 1)
            self.assertEqual(window._title_bar.height(), 36)
            control = window._title_bar.minimize
            self.assertEqual(control.geometry().top(), 4)
            self.assertEqual(window._title_bar.close_button.geometry().right(), window.width() - 9)
            QTest.mouseClick(window._title_bar.maximize, Qt.MouseButton.LeftButton)
            self.app.processEvents()
            self.assertTrue(window.isMaximized())
            self.assertFalse(window._title_bar.maximize.property('keyboardFocus'))
            self.assertEqual(window._hit_test(1, 1), 2)
            self.assertEqual(window._title_bar.maximize.accessibleName(), 'Restaurer')
            QTest.mouseClick(window._title_bar.maximize, Qt.MouseButton.LeftButton)
            self.app.processEvents()
            self.assertFalse(window.isMaximized())
            self.assertEqual(window.size().toTuple(), (1000, 700))
            QTest.mouseDClick(window._title_bar, Qt.MouseButton.LeftButton, pos=QPoint(300, 15))
            self.app.processEvents()
            self.assertTrue(window.isMaximized())
            QTest.mouseClick(window._title_bar.minimize, Qt.MouseButton.LeftButton)
            self.app.processEvents()
            self.assertTrue(window.isMinimized())
            window.showNormal()
            QTest.mouseClick(window._title_bar.close_button, Qt.MouseButton.LeftButton)
            self.assertFalse(window.isVisible())
        finally:
            window.close()
            window.deleteLater()
            self.app.processEvents()

    def test_tag_page_edit_search_draft_confirmation_and_key_preservation(self):
        from ui.tag_page import TagPage
        self.create("demo")
        private_before = (s.SSH_DIR / "demo").read_bytes()
        tag = m.create_tag("Alpha", "#2197FE")
        other = m.create_tag("Beta", "#8453BF")
        m.set_key_tag("demo", tag)
        page = TagPage()
        page.set_keys(s.scan_keys())
        changes = []
        page.changed.connect(lambda: changes.append(True))
        try:
            self.assertEqual(page._editing_id, tag)
            self.assertIn("1 clé", page._usage.text())
            page._name.setText("Serveurs")
            page._hex.setText("#123456")
            page._save()
            self.assertEqual(m.get_key_tag("demo"), (tag, "Serveurs", "#123456"))
            self.assertFalse(page._save_btn.isEnabled())
            page._name.setText("Brouillon")
            target = next(page._list.item(i) for i in range(page._list.count())
                          if page._list.item(i).data(256)['id'] == other)
            page._list.setCurrentItem(target)
            self.assertEqual(page._editing_id, tag)
            self.assertEqual(page._name.text(), "Brouillon")
            self.assertIsNotNone(page._pending_action)
            page._confirm_notice()
            self.assertEqual(page._editing_id, other)
            self.assertEqual(page._name.text(), "Beta")
            page._search.setText("SERVEURS")
            self.assertEqual(sum(not page._list.item(i).isHidden() for i in range(page._list.count())), 1)
            page._search.clear()
            page._load_tag(tag)
            page._request_delete()
            self.assertIsNotNone(m.get_tag(tag))
            page._cancel_notice()
            self.assertIsNotNone(m.get_tag(tag))
            page._request_delete()
            page._confirm_notice()
            self.assertIsNone(m.get_tag(tag))
            self.assertEqual(m.get_key_tag("demo"), ("", "", ""))
            self.assertEqual((s.SSH_DIR / "demo").read_bytes(), private_before)
            self.assertEqual(len(changes), 2)
            page._request_new()
            page._name.setText("Beta")
            page._save()
            self.assertIn("existe déjà", page._feedback.text())
            self.assertFalse(page._feedback.isHidden())
            page._name.setText("Nouveau")
            page._save()
            self.assertEqual(m.get_tag(page._editing_id)['label'], "Nouveau")
        finally:
            page.deleteLater()
            self.app.processEvents()

    def test_tag_selector_round_corners_keyboard_and_identity(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from ui.widgets.tag_dialog import TagAssignWidget
        tag = m.create_tag("Sélection", "#2197FE")
        widget = TagAssignWidget()
        widget.resize(500, 100)
        widget.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        widget.show()
        try:
            combo = widget._combo
            combo.showPopup()
            self.app.processEvents()
            popup = combo._popup
            image = popup.grab().toImage()
            self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
            self.assertEqual(image.pixelColor(image.width() - 1, image.height() - 1).alpha(), 0)
            self.assertEqual(image.pixelColor(image.width() // 2, image.height() // 2).alpha(), 255)
            self.assertEqual(popup.list.verticalScrollBar().maximum(), 0)
            self.assertTrue(popup.list.viewport().rect().contains(popup.list.visualItemRect(popup.list.item(1))))
            QTest.keyClick(popup.list, Qt.Key.Key_Down)
            QTest.keyClick(popup.list, Qt.Key.Key_Return)
            self.assertEqual(widget.selected_tag_id(), tag)
            self.assertFalse(popup.isVisible())
            combo.showPopup()
            self.app.processEvents()
            QTest.keyClick(popup.list, Qt.Key.Key_Escape)
            self.assertFalse(popup.isVisible())
            self.assertEqual(widget.selected_tag_id(), tag)
            for i in range(20):
                combo.addItem(f'Tag {i}', f'fixture-{i}')
            combo.showPopup()
            self.app.processEvents()
            self.assertLessEqual(popup.height(), 342)
            self.assertGreater(popup.list.verticalScrollBar().maximum(), 0)
            QTest.keyClick(popup.list, Qt.Key.Key_End)
            QTest.keyClick(popup.list, Qt.Key.Key_Return)
            self.assertEqual(widget.selected_tag_id(), 'fixture-19')
        finally:
            widget.close()
            widget.deleteLater()
            self.app.processEvents()

    def test_tag_page_navigation_live_refresh_and_compact_confirmation(self):
        from PySide6.QtCore import QSettings, Qt
        from ui.main_window import MainWindow
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(self.root))
        self.create('demo')
        window = MainWindow()

        def wait_refresh():
            deadline = time.monotonic() + 10
            while window._task and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(.01)
            self.assertIsNone(window._task)

        try:
            wait_refresh()
            window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
            window.resize(920, 640)
            window.show()
            with patch('ui.main_window.QInputDialog.getItem', side_effect=AssertionError('Pas de sélection native')):
                window._tags_nav.click()
            page = window._tag_page
            self.app.processEvents()
            self.assertIs(window._pages.currentWidget(), page)
            self.assertIsNone(page._editing_id)
            page._name.setText('Production')
            page._save_btn.click()
            wait_refresh()
            tag = page._editing_id
            m.set_key_tag('demo', tag)
            window.refresh_keys()
            wait_refresh()
            self.assertIn('1 clé', page._usage.text())
            page._name.setText('Serveurs')
            page._save_btn.click()
            wait_refresh()
            self.assertEqual(window._keys_model._keys[0].tag_label, 'Serveurs')
            self.assertEqual(window._tag_filter._buttons[tag].text(), 'Serveurs')
            page._name.setText('Brouillon conservé')
            window._all_nav.click()
            self.assertEqual(window._pages.currentIndex(), 0)
            window._tags_nav.click()
            self.assertEqual(page._name.text(), 'Brouillon conservé')
            self.app.processEvents()
            self.assertTrue(page.rect().contains(page._save_btn.mapTo(page, page._save_btn.rect().bottomRight())))
            page._request_delete()
            self.app.processEvents()
            self.assertTrue(page._save_btn.isHidden())
            self.assertTrue(page.rect().contains(page._confirm_btn.mapTo(page, page._confirm_btn.rect().bottomRight())))
            page._cancel_notice()
            self.assertTrue(page._save_btn.isVisible())
            self.assertEqual(m.get_key_tag('demo')[0], tag)
        finally:
            window.close()
            window.deleteLater()
            self.app.processEvents()

    def test_background_refresh_dialogs_and_date_sort(self):
        from PySide6.QtCore import QSettings
        from ui.main_window import MainWindow
        from ui.key_create_dialog import KeyCreateDialog
        from ui.key_detail_dialog import KeyDetailDialog
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(self.root))
        self.create()
        window = MainWindow()
        deadline = time.monotonic() + 10
        while getattr(window, "_task", None) and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.assertIsNone(window._task)
        self.assertEqual(window._keys_model.rowCount(), 1)
        create = KeyCreateDialog(window)
        detail = KeyDetailDialog(s.scan_keys()[0], window)
        window.show()
        self.app.processEvents()
        self.assertTrue(window.grab().save(str(self.root / "main.png")))
        detail.show()
        self.app.processEvents()
        self.assertTrue(detail.grab().save(str(self.root / "details.png")))
        create.close()
        detail.close()
        window.close()
        window.deleteLater()
        self.app.processEvents()

    def test_create_without_server_in_background(self):
        from ui.key_create_dialog import KeyCreateDialog
        from PySide6.QtWidgets import QDialog
        dialog = KeyCreateDialog()
        dialog._name.setText("personal")
        dialog._comment.setText("Commentaire complet")
        dialog._passphrase.setText("test secret")
        dialog._confirm.setText("test secret")
        dialog._on_create()
        deadline = time.monotonic() + 10
        while getattr(dialog, "_task", None) and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.assertIsNone(dialog._task)
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertFalse(s.SSH_CONFIG.exists())
        self.assertEqual(s.scan_keys()[0].comment, "Commentaire complet")
        dialog.deleteLater()
        self.app.processEvents()

    def test_date_sort_uses_timestamps_and_deleted_filter_resets(self):
        from PySide6.QtCore import Qt
        from ui.main_window import KeysTableModel, KeysFilterProxyModel
        from ui.widgets.tags import TagFilterBar
        self.create("old")
        self.create("new")
        keys = s.scan_keys()
        for key in keys:
            key.created_at = datetime(2026, 1, 31) if key.name == "old" else datetime(2026, 2, 1)
        model = KeysTableModel(keys)
        proxy = KeysFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setSortRole(Qt.ItemDataRole.UserRole + 1)
        proxy.sort(5, Qt.SortOrder.AscendingOrder)
        self.assertEqual(proxy.index(0, 1).data(), "old")
        tag = m.create_tag("Deleted", "#3B82F6")
        bar = TagFilterBar()
        bar._on_click(tag)
        m.delete_tag(tag)
        changes = []
        bar.filter_changed.connect(changes.append)
        bar.rebuild()
        self.assertEqual(bar._active, "all")
        self.assertEqual(changes, ["all"])
        bar.deleteLater()
        self.app.processEvents()

    def test_selection_preview_combined_filters_and_compact_actions(self):
        from PySide6.QtCore import QSettings
        from PySide6.QtGui import QGuiApplication
        from ui.main_window import MainWindow
        self.create("alpha", passphrase="test secret")
        self.create("zulu")
        tag = m.create_tag("Serveur", "#22C55E")
        m.set_key_tag("zulu", tag)
        keys = s.scan_keys()
        next(k for k in keys if k.name == "zulu").warning = "À vérifier pour ce test"
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(self.root))
        with patch.object(s, "scan_keys", return_value=keys):
            window = MainWindow()
            deadline = time.monotonic() + 10
            while window._task and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(.01)
        try:
            self.assertIsNone(window._task)
            self.assertEqual(window._selected_key().name, "alpha")
            self.assertEqual(window._preview_values["PROTECTION"].text(), "Passphrase")
            self.assertEqual(window._summary_total.value.text(), "2")
            self.assertEqual(window._summary_protected.value.text(), "1")
            self.assertEqual(window._summary_warnings.value.text(), "1")
            window._set_view(True)
            window._on_tag_filter(tag)
            self.app.processEvents()
            self.assertEqual(window._keys_proxy.rowCount(), 1)
            self.assertEqual(window._selected_key().name, "zulu")
            self.assertEqual(window._preview_name.text(), "zulu")
            window._on_copy_public()
            self.assertEqual(QGuiApplication.clipboard().text(), s.read_public_key("zulu")[0])
            window._search.setText("introuvable")
            self.app.processEvents()
            self.assertEqual(window._list_stack.currentIndex(), 1)
            self.assertFalse(window._copy_btn.isEnabled())
            self.assertEqual(window._summary_total.value.text(), "2")
            self.assertEqual(window._summary_protected.value.text(), "1")
            self.assertEqual(window._summary_warnings.value.text(), "1")
            window._search.clear()
            window.show()
            window.resize(920, 580)
            self.app.processEvents()
            self.assertFalse(window._preview_card.isVisible())
            self.assertTrue(window._compact_actions.isVisible())
            self.assertTrue(window._compact_copy.isEnabled())
            self.assertFalse(window._summary_strip.isVisible())
            window.resize(1280, 800)
            self.app.processEvents()
            self.assertTrue(window._preview_card.isVisible())
            self.assertFalse(window._compact_actions.isVisible())
            self.assertTrue(window._summary_strip.isVisible())
        finally:
            window.close()
            window.deleteLater()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
