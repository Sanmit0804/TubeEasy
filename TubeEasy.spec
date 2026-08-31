# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

block_cipher = None

# Base path of the repository
BASE_DIR = Path(SPECPATH).resolve()

# Bundled data files (source, destination in bundle)
datas = [
    (str(BASE_DIR / 'assets'), 'assets'),
    (str(BASE_DIR / 'app' / 'ui' / 'styles'), 'app/ui/styles'),
    (str(BASE_DIR / 'ffmpeg'), 'ffmpeg'),
]

# Binaries to include directly
binaries = []

hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'yt_dlp',
    'yt_dlp.compat',
    'yt_dlp.utils',
    'yt_dlp.extractor',
    'yt_dlp.downloader',
    'yt_dlp.postprocessor',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
]

a = Analysis(
    [str(BASE_DIR / 'app' / 'main.py')],
    pathex=[str(BASE_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'numpy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TubeEasy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # No command prompt window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(BASE_DIR / 'assets' / 'app_icon.ico')
)