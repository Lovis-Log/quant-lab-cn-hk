# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir recipe for the pywebview + Streamlit desktop shell."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata


ROOT = Path(SPECPATH).resolve()
datas = [
    (str(ROOT / "VERSION"), "."),
    (str(ROOT / "app.py"), "."),
    (str(ROOT / ".streamlit" / "config.toml"), ".streamlit"),
    (str(ROOT / "quant_lab" / "terminal.css"), "quant_lab"),
    (str(ROOT / "assets" / "quantlab.ico"), "assets"),
]
binaries = []
hiddenimports = collect_submodules("quant_lab") + [
    "streamlit.web.cli",
    "streamlit.web.bootstrap",
    "webview.platforms.edgechromium",
]

for package in ("streamlit", "webview", "plotly", "altair", "akshare"):
    package_data, package_binaries, package_hidden = collect_all(package)
    datas += package_data
    binaries += package_binaries
    hiddenimports += package_hidden
    try:
        datas += copy_metadata("pywebview" if package == "webview" else package)
    except Exception:
        pass

analysis = Analysis(
    [str(ROOT / "desktop_launcher.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "playwright"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="QuantLab",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "assets" / "quantlab.ico"),
)
coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="QuantLab",
)
