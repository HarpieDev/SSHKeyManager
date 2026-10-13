"""Écritures atomiques et permissions des fichiers locaux."""
from core.i18n import tr
import ctypes
import os
import tempfile
from ctypes import wintypes
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _windows_security():
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    adv.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    adv.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    adv.ConvertSidToStringSidW.argtypes = [wintypes.LPVOID, ctypes.POINTER(wintypes.LPWSTR)]
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.LPVOID), ctypes.POINTER(wintypes.DWORD)]
    adv.SetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPVOID]
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [wintypes.LPVOID]
    kernel.LocalFree.restype = wintypes.LPVOID
    token = wintypes.HANDLE()
    if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        size = wintypes.DWORD()
        adv.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        buf = ctypes.create_string_buffer(size.value)
        if not adv.GetTokenInformation(token, 1, buf, size, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        sid = ctypes.cast(buf, ctypes.POINTER(wintypes.LPVOID))[0]
        text = wintypes.LPWSTR()
        if not adv.ConvertSidToStringSidW(sid, ctypes.byref(text)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return adv, kernel, text.value
        finally:
            kernel.LocalFree(ctypes.cast(text, wintypes.LPVOID))
    finally:
        kernel.CloseHandle(token)


def protect_private(path: Path) -> None:
    """Autorise seulement le propriétaire, SYSTEM et les administrateurs Windows."""
    if os.name != "nt":
        path.chmod(0o700 if path.is_dir() else 0o600)
        return
    adv, kernel, sid = _windows_security()
    inheritance = "OICI" if path.is_dir() else ""
    sddl = f"D:P(A;{inheritance};FA;;;{sid})(A;{inheritance};FA;;;SY)(A;{inheritance};FA;;;BA)"
    descriptor = wintypes.LPVOID()
    if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, ctypes.byref(descriptor), None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not adv.SetFileSecurityW(str(path), 0x80000004, descriptor):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.LocalFree(descriptor)


def private_permission_warning(path: Path) -> str:
    if os.name != "nt":
        return tr('Permissions trop ouvertes sur la clé privée.') if path.stat().st_mode & 0o077 else ""
    adv, kernel, sid = _windows_security()
    adv.GetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, ctypes.c_int, wintypes.DWORD, wintypes.LPVOID, wintypes.LPVOID, ctypes.POINTER(wintypes.LPVOID), wintypes.LPVOID, ctypes.POINTER(wintypes.LPVOID)]
    adv.GetAce.argtypes = [wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.LPVOID)]
    dacl, descriptor = wintypes.LPVOID(), wintypes.LPVOID()
    result = adv.GetNamedSecurityInfoW(str(path), 1, 4, None, None, ctypes.byref(dacl), None, ctypes.byref(descriptor))
    if result:
        return tr('Permissions Windows non vérifiables.')
    try:
        if not dacl:
            return tr('Permissions trop ouvertes sur la clé privée.')
        count = ctypes.c_ushort.from_address(dacl.value + 4).value
        for i in range(count):
            ace = wintypes.LPVOID()
            if not adv.GetAce(dacl, i, ctypes.byref(ace)):
                return tr('Permissions Windows non vérifiables.')
            kind = ctypes.c_ubyte.from_address(ace.value).value
            flags = ctypes.c_ubyte.from_address(ace.value + 1).value
            if flags & 8:  # INHERIT_ONLY_ACE
                continue
            if kind not in (0, 5):  # ACCESS_ALLOWED / ACCESS_ALLOWED_OBJECT
                continue
            if kind == 5:
                return tr('Permissions Windows spécifiques : vérification manuelle nécessaire.')
            text = wintypes.LPWSTR()
            if not adv.ConvertSidToStringSidW(wintypes.LPVOID(ace.value + 8), ctypes.byref(text)):
                return tr('Permissions Windows non vérifiables.')
            try:
                if text.value not in {sid, "S-1-5-18", "S-1-5-32-544"}:
                    return tr("La clé privée est accessible à d'autres comptes Windows.")
            finally:
                kernel.LocalFree(ctypes.cast(text, wintypes.LPVOID))
        return ""
    finally:
        kernel.LocalFree(descriptor)


def atomic_write(path: Path, data: bytes, *, private: bool = False, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError(tr('Un lien symbolique ne peut pas être modifié.'))
    fd, temp_name = tempfile.mkstemp(prefix=".harpie-", dir=path.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            if private:
                protect_private(temp)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if exclusive:
            # Windows rename refuse une destination existante ; link fait de même sur POSIX.
            if os.name == "nt":
                temp.rename(path)
            else:
                os.link(temp, path)
                temp.unlink()
        else:
            os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
