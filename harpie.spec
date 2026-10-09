# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# Qt utilise les DLL ICU natives de Windows. Une DLL homonyme issue de Poppler,
# Git ou d'un autre outil dans PATH peut être incompatible et casser le démarrage.
a.binaries = [entry for entry in a.binaries
              if Path(entry[0]).name.lower() not in {'icuuc.dll', 'icuin.dll', 'icudt.dll', 'icu.dll'}]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Harpie',
    icon='assets/icons/harpie.ico',
    version='assets/windows_version.txt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
