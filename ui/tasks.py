"""Tâches de fond Qt : aucune commande longue dans le thread de l'interface."""
from core.i18n import tr
from PySide6.QtCore import QThread, Qt, Slot
from PySide6.QtWidgets import QMessageBox


class Task(QThread):
    def __init__(self, function, callback, *, on_error=None, parent=None):
        super().__init__(parent)
        self.function = function
        self.callback = callback
        self.on_error = on_error
        self.result = None
        self.error = ""
        self.finished.connect(self._complete, Qt.ConnectionType.QueuedConnection)

    def run(self):
        try:
            self.result = self.function()
        except Exception as exc:
            self.error = str(exc) or tr("L'opération a échoué.")
        finally:
            self.function = None

    @Slot()
    def _complete(self):
        # This QObject slot runs on the GUI thread. Join native thread cleanup
        # before a callback closes a modal dialog or starts another operation.
        self.wait()
        owner = self.parent()
        owner._task = None
        owner.setEnabled(True)
        try:
            if self.error:
                if self.on_error:
                    self.on_error(self.error)
                else:
                    QMessageBox.warning(owner, tr('Opération impossible'), self.error)
            else:
                self.callback(self.result)
        finally:
            self.callback = None
            self.on_error = None
            self.result = None
            self.deleteLater()


class BackgroundMixin:
    def run_task(self, function, callback, *, on_error=None):
        if getattr(self, "_task", None) is not None:
            return
        self.setEnabled(False)
        task = Task(function, callback, on_error=on_error, parent=self)
        self._task = task
        task.start()

    def closeEvent(self, event):
        if getattr(self, "_task", None) is not None:
            event.ignore()
            return
        super().closeEvent(event)

    def reject(self):
        if getattr(self, "_task", None) is None:
            super().reject()
