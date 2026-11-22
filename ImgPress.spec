# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（onedir）。

    python -m PyInstaller --noconfirm --clean ImgPress.spec

产物：dist/ImgPress/ImgPress.exe
工具链与资源由 build/build_exe.py 在打包后复制到 dist/ImgPress/ 下，便于替换版本。
"""

import os

from PySide6.QtCore import QLibraryInfo

# 只打包界面语言需要的 Qt 内置文案（文件对话框按钮、标准消息框等）。
# 英文是 Qt 的内置语言，不需要 .qm；新增语言时在 i18n.LANGUAGES 与这里各加一条。
QT_TRANSLATIONS = ["qtbase_zh_CN.qm"]
QT_TRANS_DIR = QLibraryInfo.path(QLibraryInfo.TranslationsPath)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'numpy', 'PIL', 'pytest', 'unittest', 'pydoc'],
    noarchive=False,
)

# PySide6 的钩子默认收集全部 99 个 .qm（约 7 MB），这里剔除后只保留白名单。
# 注意 PyInstaller 6 的 TOC 顺序是 (dest_name, src_name, typecode)。
a.datas = [
    entry
    for entry in a.datas
    if 'translations' not in entry[0].replace('\\', '/').lower()
]
for name in QT_TRANSLATIONS:
    source = os.path.join(QT_TRANS_DIR, name)
    if os.path.exists(source):
        a.datas.append((f'PySide6/translations/{name}', source, 'DATA'))
    else:
        print(f'[spec] 警告：找不到 {source}')

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ImgPress',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon='assets/icon.ico',
    version=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='ImgPress',
)
