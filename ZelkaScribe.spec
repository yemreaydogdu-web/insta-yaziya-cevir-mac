# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

block_cipher = None

hiddenimports = []
hiddenimports += collect_submodules('yt_dlp')
hiddenimports += collect_submodules('faster_whisper')
hiddenimports += collect_submodules('ctranslate2')
hiddenimports += collect_submodules('av')
hiddenimports += collect_submodules('huggingface_hub')
hiddenimports += collect_submodules('tokenizers')

binaries = []
binaries += collect_dynamic_libs('ctranslate2')
binaries += collect_dynamic_libs('av')

datas = []
datas += collect_data_files('yt_dlp')
datas += collect_data_files('faster_whisper')
datas += collect_data_files('ctranslate2')
datas += collect_data_files('certifi')
datas += [('assets', 'assets')]

a = Analysis(
    ['src/InstaYaziyaCevir.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ZelkaScribe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ZelkaScribe',
)
app = BUNDLE(
    coll,
    name='Zelka Scribe.app',
    icon='assets/ZelkaScribe.icns',
    bundle_identifier='com.zelkalabs.zelkascribe',
    info_plist={
        'CFBundleName': 'Zelka Scribe',
        'CFBundleDisplayName': 'Zelka Scribe',
        'CFBundleShortVersionString': '2.0.0',
        'CFBundleVersion': '2.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '12.0',
    },
)
