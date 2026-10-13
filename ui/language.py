"""Live translation bindings, language preference, and Qt's standard dialogs."""
from pathlib import Path
import weakref

from PySide6.QtCore import QLibraryInfo, QLocale, QSettings, QTranslator
from PySide6.QtWidgets import QApplication
from shiboken6 import isValid

from core.i18n import LocalizedText, set_language, tr
from ui.assets import ASSETS_DIR

_widgets = {}
_qt_translator = None


def set_translated(widget, method: str, text, *extra):
    """Bind explicit application text. Plain user text clears an old binding."""
    bindings = getattr(widget, '_translation_bindings', None)
    if bindings is None:
        bindings = widget._translation_bindings = {}
    if isinstance(text, LocalizedText):
        bindings[method] = (text, extra)
        identity = id(widget)
        _widgets[identity] = weakref.ref(widget, lambda ref, key=identity: _widgets.pop(key, None))
    else:
        bindings.pop(method, None)
    getattr(widget, method)(str(text), *extra)


def localized(widget, text):
    set_translated(widget, 'setText', text)
    return widget


def add_translated_item(combo, text, *extra):
    index = combo.count()
    combo.addItem(str(text), *extra)
    if isinstance(text, LocalizedText):
        combo._translated_items = getattr(combo, '_translated_items', {})
        combo._translated_items[index] = text
        _widgets[id(combo)] = weakref.ref(combo)


def add_translated_tab(tabs, widget, text):
    index = tabs.addTab(widget, str(text))
    tabs._translated_tabs = getattr(tabs, '_translated_tabs', {})
    tabs._translated_tabs[index] = text
    _widgets[id(tabs)] = weakref.ref(tabs)
    return index


def initialize_language(override=None):
    preferred = override or QSettings().value('ui/language', '')
    if preferred not in ('fr', 'en'):
        preferred = 'fr' if QLocale.system().name().startswith('fr') else 'en'
    change_language(preferred, persist=bool(override))


def change_language(value: str, *, persist=True):
    global _qt_translator
    set_language(value)
    if persist:
        QSettings().setValue('ui/language', value)
    app = QApplication.instance()
    if _qt_translator is not None:
        app.removeTranslator(_qt_translator)
        _qt_translator = None
    if value == 'fr':
        translator = QTranslator(app)
        paths = [ASSETS_DIR / 'locales' / 'qtbase_fr.qm',
                 Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)) / 'qtbase_fr.qm']
        if any(translator.load(str(path)) for path in paths):
            app.installTranslator(translator)
            _qt_translator = translator
    for identity, ref in list(_widgets.items()):
        widget = ref()
        if widget is None or not isValid(widget):
            _widgets.pop(identity, None)
            continue
        for method, (text, extra) in getattr(widget, '_translation_bindings', {}).items():
            getattr(widget, method)(str(tr(text)), *extra)
        for index, text in getattr(widget, '_translated_items', {}).items():
            if index < widget.count():
                widget.setItemText(index, str(tr(text)))
        for index, text in getattr(widget, '_translated_tabs', {}).items():
            widget.setTabText(index, str(tr(text)))
