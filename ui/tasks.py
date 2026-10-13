"""Tâches de fond Qt : aucune commande longue dans le thread de l'interface."""
from core.i18n import tr
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QMessageBox


class Task(QThread):
    def __init__(self, function, parent=None):
        super().__init__(parent)
        self.function = function
        self.result = None
        self.error = ""

    def run(self):
        try:
            self.result = self.function()
        except Exception as exc:
            self.error = str(exc) or tr("L'opération a échoué.")
        finally:
            self.function = None


class BackgroundMixin:
    def run_task(self, function, callback, *, on_error=None):
        if getattr(self, "_task", None) is not None:
            return
        self.setEnabled(False)
        task = Task(function, self)
        self._task = task

        def completed():
            self._task = None
            self.setEnabled(True)
            if task.error:
                if on_error:
                    on_error(task.error)
                else:
                    QMessageBox.warning(self, tr('Opération impossible'), task.error)
            else:
                callback(task.result)
            task.deleteLater()

        task.finished.connect(completed)
        task.start()

    def closeEvent(self, event):
        if getattr(self, "_task", None) is not None:
            event.ignore()
            return
        super().closeEvent(event)

    def reject(self):
        if getattr(self, "_task", None) is None:
            super().reject()
