# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Neology Average Speed
# Run with: pyinstaller neology_average_speed.spec

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect pyproj data files (proj database needed at runtime)
pyproj_datas = collect_data_files('pyproj')

# Collect certifi CA bundle (used by requests/urllib internally)
try:
    certifi_datas = collect_data_files('certifi')
except Exception:
    certifi_datas = []

a = Analysis(
    ['neology_average_speed.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # UI file - loaded at runtime via uic.loadUi()
        ('ui/neology_average_speed.ui', 'ui'),
        # Default JSON config - loaded from resourcesPath (cwd) by the app
        # This is placed in the _MEIPASS root so it is available next to the exe
        # at runtime via the installer (see InnoSetup script).
        # ('neology_average_speed.json', '.'),  # Uncomment if you want it bundled
    ] + pyproj_datas + certifi_datas,
    hiddenimports=[
        # PyQt5 plugins that PyInstaller sometimes misses
        'PyQt5.sip',
        'PyQt5.QtPrintSupport',
        # pyproj / PROJ runtime
        'pyproj',
        'pyproj.datadir',
        # geopy
        'geopy.distance',
        'geopy.geocoders',
        # utm coordinate library
        'utm',
        # openpyxl internals
        'openpyxl.cell._writer',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',   # remove if you add numpy usage later
        'scipy',
        'pandas',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NeologyAverageSpeed',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # Windowed app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='neology2.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NeologyAverageSpeed',
)
