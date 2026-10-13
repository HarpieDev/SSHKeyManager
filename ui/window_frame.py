"""Fenêtre intégrée au design, avec déplacement et redimensionnement Windows."""
from core.i18n import tr
from ui.language import set_translated
import ctypes
from ctypes import wintypes
import sys

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QPushButton, QWidget


class WindowControl(QPushButton):
    def __init__(self, kind, callback, parent):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(44, 28)
        self.setObjectName('WindowClose' if kind == 'close' else 'WindowControl')
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.clicked.connect(callback)
        self.restored = False
        self.setProperty('keyboardFocus', False)

    def _keyboard_focus(self, enabled):
        self.setProperty('keyboardFocus', enabled)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def focusInEvent(self, event):
        self._keyboard_focus(event.reason() in (Qt.FocusReason.TabFocusReason,
                                               Qt.FocusReason.BacktabFocusReason,
                                               Qt.FocusReason.ShortcutFocusReason))
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._keyboard_focus(False)
        super().focusOutEvent(event)

    def mousePressEvent(self, event):
        self._keyboard_focus(False)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#F5F5F7'), 1.2))
        painter.translate(self.width() / 2, self.height() / 2)
        if self.kind == 'minimize':
            painter.drawLine(QPoint(-5, 1), QPoint(5, 1))
        elif self.kind == 'close':
            painter.drawLine(QPoint(-4, -4), QPoint(4, 4))
            painter.drawLine(QPoint(-4, 4), QPoint(4, -4))
        elif self.restored:
            painter.drawRect(-3, -5, 8, 8)
            painter.fillRect(-5, -3, 8, 8, QColor('#252B35' if self.underMouse() else '#0C0E12'))
            painter.drawRect(-5, -3, 8, 8)
        else:
            painter.drawRect(-5, -5, 10, 10)


class WindowTitleBar(QWidget):
    HEIGHT = 36

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setObjectName('WindowTitleBar')
        self.setFixedHeight(self.HEIGHT)
        set_translated(self, 'setAccessibleName', tr('Contrôles de la fenêtre Harpie'))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 8, 4)
        layout.setSpacing(2)
        layout.addStretch()
        self.minimize = WindowControl('minimize', owner.showMinimized, self)
        self.maximize = WindowControl('maximize', owner.toggle_maximized, self)
        self.close_button = WindowControl('close', owner.close, self)
        for control, name in ((self.minimize, tr('Réduire')), (self.maximize, tr('Agrandir')),
                              (self.close_button, tr('Fermer'))):
            set_translated(control, 'setAccessibleName', name)
            set_translated(control, 'setToolTip', name)
            layout.addWidget(control)

    def update_state(self):
        self.maximize.restored = self.owner.isMaximized()
        text = tr('Restaurer') if self.maximize.restored else tr('Agrandir')
        set_translated(self.maximize, 'setToolTip', text)
        set_translated(self.maximize, 'setAccessibleName', text)
        self.maximize.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.owner.windowHandle():
            self.owner.windowHandle().startSystemMove()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.owner.toggle_maximized()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


class MonitorInfo(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('monitor', wintypes.RECT),
                ('work', wintypes.RECT), ('flags', wintypes.DWORD)]


class MinMaxInfo(ctypes.Structure):
    _fields_ = [('reserved', wintypes.POINT), ('max_size', wintypes.POINT),
                ('max_position', wintypes.POINT), ('min_track', wintypes.POINT),
                ('max_track', wintypes.POINT)]


class IntegratedWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowSystemMenuHint
                            | Qt.WindowType.WindowMinimizeButtonHint
                            | Qt.WindowType.WindowMaximizeButtonHint)
        self._native_frame = sys.platform == 'win32' and QApplication.platformName() == 'windows'
        self._frame_handle = None
        self.setObjectName('HarpieWindow')
        self._title_bar = WindowTitleBar(self)
        self.setMenuWidget(self._title_bar)
        if self._native_frame:
            self._setup_win_api()
            QShortcut(QKeySequence('Alt+Space'), self, activated=self._system_menu)

    def _setup_win_api(self):
        self._win = ctypes.WinDLL('user32', use_last_error=True)
        signatures = {
            'GetWindowLongPtrW': ([wintypes.HWND, ctypes.c_int], ctypes.c_ssize_t),
            'SetWindowLongPtrW': ([wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t], ctypes.c_ssize_t),
            'SetWindowPos': ([wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                              ctypes.c_int, ctypes.c_int, wintypes.UINT], wintypes.BOOL),
            'GetWindowRect': ([wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            'ScreenToClient': ([wintypes.HWND, ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
            'IsZoomed': ([wintypes.HWND], wintypes.BOOL),
            'MonitorFromWindow': ([wintypes.HWND, wintypes.DWORD], wintypes.HANDLE),
            'MonitorFromRect': ([ctypes.POINTER(wintypes.RECT), wintypes.DWORD], wintypes.HANDLE),
            'GetMonitorInfoW': ([wintypes.HANDLE, ctypes.POINTER(MonitorInfo)], wintypes.BOOL),
            'GetSystemMenu': ([wintypes.HWND, wintypes.BOOL], wintypes.HMENU),
            'TrackPopupMenu': ([wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, wintypes.HWND, ctypes.c_void_p], wintypes.UINT),
            'PostMessageW': ([wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM], wintypes.BOOL),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self._win, name)
            function.argtypes, function.restype = args, result

    def _install_native_frame(self):
        handle = int(self.winId())
        if self._frame_handle == handle:
            return
        self._frame_handle = handle
        # Conserver les fonctions natives (Snap, ombre, menu système), puis
        # supprimer uniquement le dessin de la barre et des bordures via NCCALCSIZE.
        style = self._win.GetWindowLongPtrW(handle, -16)
        self._win.SetWindowLongPtrW(handle, -16, style | 0x00CF0000)
        self._win.SetWindowPos(handle, None, 0, 0, 0, 0, 0x0037)
        dwm = ctypes.WinDLL('dwmapi')
        dwm.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD,
                                             ctypes.c_void_p, wintypes.DWORD]
        dwm.DwmExtendFrameIntoClientArea.argtypes = [wintypes.HWND, ctypes.c_void_p]
        margins = (ctypes.c_int * 4)(1, 1, 1, 1)
        dwm.DwmExtendFrameIntoClientArea(handle, ctypes.byref(margins))
        for attribute, value in ((33, 2), (34, 0xFFFFFFFE)):
            data = ctypes.c_uint(value)
            dwm.DwmSetWindowAttribute(handle, attribute, ctypes.byref(data), ctypes.sizeof(data))

    def toggle_maximized(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def showEvent(self, event):
        super().showEvent(event)
        if self._native_frame:
            self._install_native_frame()
        self._position_controls()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_title_bar'):
            self._position_controls()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and hasattr(self, '_title_bar'):
            self._title_bar.update_state()

    def _position_controls(self):
        self._title_bar.raise_()
        self._title_bar.update_state()

    def _hit_test(self, x, y):
        """Coordonnées logiques relatives à la fenêtre ; constantes HT Windows."""
        if not self.isMaximized() and not self.isFullScreen():
            left, right = x < 6, x >= self.width() - 6
            top, bottom = y < 6, y >= self.height() - 6
            if top and left: return 13
            if top and right: return 14
            if bottom and left: return 16
            if bottom and right: return 17
            if left: return 10
            if right: return 11
            if top: return 12
            if bottom: return 15
        if 0 <= y < WindowTitleBar.HEIGHT and 0 <= x < self.width():
            point = QPoint(int(x), int(y))
            for control in (self._title_bar.minimize, self._title_bar.maximize, self._title_bar.close_button):
                if control.geometry().contains(point):
                    return 1
            return 2  # HTCAPTION : déplacement dans le bandeau, marges comprises.
        return 1  # HTCLIENT : Qt reçoit les clics sur les boutons et les champs.

    def nativeEvent(self, event_type, message):
        if getattr(self, '_native_frame', False):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0083:  # WM_NCCALCSIZE : client sur toute la surface.
                if hasattr(self, '_win') and self._win.IsZoomed(msg.hWnd):
                    # Windows peut proposer un rectangle qui déborde de 8 px lors
                    # de la maximisation. Garder le client dans la zone de travail.
                    rect = wintypes.RECT.from_address(msg.lParam)
                    monitor = self._win.MonitorFromRect(ctypes.byref(rect), 2)
                    info = MonitorInfo(size=ctypes.sizeof(MonitorInfo))
                    if self._win.GetMonitorInfoW(monitor, ctypes.byref(info)):
                        rect.left = max(rect.left, info.work.left)
                        rect.top = max(rect.top, info.work.top)
                        rect.right = min(rect.right, info.work.right)
                        rect.bottom = min(rect.bottom, info.work.bottom)
                return True, 0
            if msg.message == 0x0084 and hasattr(self, '_win'):  # WM_NCHITTEST.
                point = wintypes.POINT(ctypes.c_short(msg.lParam & 0xFFFF).value,
                                       ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value)
                if self._win.ScreenToClient(msg.hWnd, ctypes.byref(point)):
                    ratio = self.devicePixelRatioF()
                    return True, self._hit_test(point.x / ratio, point.y / ratio)
            if msg.message == 0x0024 and hasattr(self, '_win'):  # WM_GETMINMAXINFO.
                monitor = self._win.MonitorFromWindow(msg.hWnd, 2)
                info = MonitorInfo(size=ctypes.sizeof(MonitorInfo))
                if self._win.GetMonitorInfoW(monitor, ctypes.byref(info)):
                    limits = MinMaxInfo.from_address(msg.lParam)
                    limits.max_position.x = info.work.left - info.monitor.left
                    limits.max_position.y = info.work.top - info.monitor.top
                    limits.max_size.x = info.work.right - info.work.left
                    limits.max_size.y = info.work.bottom - info.work.top
                    # Qt fournit les contraintes mini : les conserver.
                    ratio = self.devicePixelRatioF()
                    limits.min_track.x = max(limits.min_track.x, round(self.minimumWidth() * ratio))
                    limits.min_track.y = max(limits.min_track.y, round(self.minimumHeight() * ratio))
                    return True, 0
        return super().nativeEvent(event_type, message)

    def _system_menu(self):
        handle = int(self.winId())
        rect = wintypes.RECT()
        if not self._win.GetWindowRect(handle, ctypes.byref(rect)):
            return
        menu = self._win.GetSystemMenu(handle, False)
        command = self._win.TrackPopupMenu(menu, 0x0100 | 0x0002,
                                           rect.left + 8, rect.top + round(WindowTitleBar.HEIGHT * self.devicePixelRatioF()),
                                           0, handle, None)
        if command:
            self._win.PostMessageW(handle, 0x0112, command, 0)
