# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import ssl
import sys

ROOT = Path(SPECPATH).resolve().parent
APP = ROOT / 'app'
NATIVE_LIBRARY = 'itm.dll' if sys.platform == 'win32' else 'libitm.dylib'
NATIVE_PATH = APP / NATIVE_LIBRARY
SSL_PATCH_CERT = Path(ssl.__file__).resolve().with_name('codex-rejected-cas.pem')
SSL_DATA = [(str(SSL_PATCH_CERT), '.') ] if SSL_PATCH_CERT.is_file() else []

a = Analysis(
    [str(APP / 'plotter.py')],
    pathex=[str(APP)],
    binaries=[(str(NATIVE_PATH), '.')],
    datas=SSL_DATA,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='One-Click-Mesh',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='One-Click-Mesh.app',
        bundle_identifier='org.indianameshalliance.oneclickmesh',
        info_plist={
            'CFBundleName': 'One Click Mesh',
            'CFBundleDisplayName': 'One Click Mesh',
            'LSMinimumSystemVersion': '12.0',
            'NSHighResolutionCapable': 'True',
        },
    )
