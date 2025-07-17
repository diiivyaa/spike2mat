# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/830.svg', 'assets'),('assets/7178736_11911.jpg', 'assets'), ('assets/fa-solid-900.ttf', 'assets'), \
    ('assets/icons8-help-50.png', 'assets'), ('assets/icon.ico', 'assets'), ('assets/step1.png', 'assets'), \
    ('assets/step2.png', 'assets'), ('assets/step3.png', 'assets'), ('assets/info.png', 'assets')],
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
    a.binaries,
    a.datas,
    [],
    name='app',
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
    icon='C:/Users/Admin/UniBE/spike-sort/src/app/assets/icon.ico',
)
