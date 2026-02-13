# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for badge-osc-server
# Build with: pyinstaller badge-osc-server.spec

import sys
import platform
from PyInstaller.utils.hooks import collect_submodules

# Collect all bleak submodules (platform-specific backends)
bleak_hiddenimports = collect_submodules('bleak')

# Collect all badge_controller submodules
badge_hiddenimports = collect_submodules('badge_controller')

# dbus-fast is Linux-only (used by bleak's bluezdbus backend)
dbus_imports = []
if platform.system() == 'Linux':
    dbus_imports = [
        'dbus_fast',
        'dbus_fast.aio',
        'dbus_fast.service',
        'dbus_fast.message',
        'dbus_fast.constants',
        'dbus_fast.signature',
        'dbus_fast.introspection',
        'dbus_fast.message_bus',
        'dbus_fast.auth',
    ]

# Exclude unused stdlib and cross-platform modules to reduce size
excludes = [
    'tkinter', '_tkinter',
    'unittest',
    'xmlrpc',
    'pydoc',
    'doctest',
    'test',
    'multiprocessing.popen_spawn_win32',
]

a = Analysis(
    ['osc_server/server.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=(
        bleak_hiddenimports
        + badge_hiddenimports
        + dbus_imports
        + [
            'pythonosc',
            'pythonosc.osc_server',
            'pythonosc.dispatcher',
            'pythonosc.udp_client',
            'Crypto',
            'Crypto.Cipher',
            'Crypto.Cipher.AES',
        ]
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='badge-osc-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
