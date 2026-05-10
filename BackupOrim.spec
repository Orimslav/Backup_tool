# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['backup_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('img/', 'img/'),
    ],
    hiddenimports=[
        'winotify',
        'pystray._win32',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.PngImagePlugin',
        'PIL.IcoImagePlugin',
        'pyzipper',
        'pyzipper.zipfile_aes',
        'winreg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'scipy', 'pandas'],
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
    name='BackupOrim',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    hide_console='hide-early',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='img/orimslav_logo_blue_transparent.ico',
)
