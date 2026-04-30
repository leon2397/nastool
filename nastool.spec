# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['nastool-cli\\nastool_cli\\main.py'],
    pathex=['D:\\project\\nastool7', 'D:\\project\\nastool7/nastool-cli', 'D:\\project\\nastool7/nastool-core', 'D:\\project\\nastool7/nastool-common', 'D:\\project\\nastool7/nastool-adapters', 'D:\\project\\nastool7/nastool-fixes', 'D:\\project\\nastool7/nastool-reporters'],
    binaries=[],
    datas=[('D:\\project\\nastool7/nastool-core/nastool_core/data', 'nastool_core/data'), ('D:\\project\\nastool7/nastool-core/create_default_config.py', '.')],
    hiddenimports=['nastool_common', 'nastool_core', 'nastool_fixes', 'nastool_reporters', 'nastool_adapters', 'websockets'],
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
    name='nastool',
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
)
