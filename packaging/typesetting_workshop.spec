# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys


project_root = Path.cwd()
entry_script = project_root / "src" / "typesetting_workshop" / "__main__.py"

a = Analysis(
    [str(entry_script)],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="typesetting-workshop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="typesetting-workshop",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="typesetting-workshop.app",
        icon=None,
        bundle_identifier=None,
    )
