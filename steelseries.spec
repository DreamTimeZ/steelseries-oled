# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for SteelSeries OLED utility."""

import sys
from pathlib import Path

block_cipher = None

# Get the project root
project_root = Path(SPECPATH)
src_dir = project_root / "src" / "steelseries_oled"
assets_dir = src_dir / "assets"

# Collect data files (fonts, etc.)
datas = []
if assets_dir.exists():
    for asset_file in assets_dir.glob("*"):
        if asset_file.is_file() and not asset_file.name.startswith("__"):
            datas.append((str(asset_file), "steelseries_oled/assets"))

# Hidden imports that PyInstaller might miss
hiddenimports = [
    "hid",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "psutil",
    "pynvml",
    "requests",
]

a = Analysis(
    [str(src_dir / "cli.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "pytest",
        "mypy",
        "ruff",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="steelseries",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(assets_dir / "icon.ico"),
)
