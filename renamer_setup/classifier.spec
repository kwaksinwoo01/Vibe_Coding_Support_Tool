# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_submodules

calamine_data, calamine_binaries, calamine_hiddenimports = collect_all("python_calamine")
win32_hiddenimports = collect_submodules("win32com") + collect_submodules("win32comext")

hiddenimports = sorted(
    set(
        calamine_hiddenimports
        + win32_hiddenimports
        + [
            "pythoncom",
            "pywintypes",
            "tkinter",
            "tkinter.ttk",
            "tkinter.messagebox",
            "pypdf",
        ]
    )
)

analysis = Analysis(
    ["launcher.py"],
    pathex=["src"],
    binaries=calamine_binaries,
    datas=calamine_data,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="classifier",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

collection = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="classifier",
)
