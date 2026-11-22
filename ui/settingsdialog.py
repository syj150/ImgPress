"""设置：工具链目录、重名策略、右键菜单注册、版本信息。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from i18n import AUTO, LANGUAGES, resolve, tr

from core import paths, registry
from core import tools as tools_mod
from core.params import CODEC_ENGINE, CODECS
from core.settings import Settings
from core.tools import Toolchain
from . import theme
from .widgets import Card, field_label, hint_label, section_label

POLICY_LABEL = {
    "overwrite": "覆盖同名文件",
    "skip": "跳过已存在的输出",
    "suffix": "自动加序号（-1、-2…）",
}


class SettingsDialog(QDialog):
    applied = Signal()

    def __init__(self, settings: Settings, tools: Toolchain, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.tools = tools
        self._initial_language = settings.language
        self.setWindowTitle(tr("设置"))
        self.setMinimumWidth(720)
        screen = QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None
        height = min(760, avail.height() - 80) if avail else 700
        self.resize(780, max(height, 560))

        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(8)
        body.addWidget(self._language_card())
        body.addWidget(self._tools_card())
        body.addWidget(self._output_card())
        body.addWidget(self._menu_card())
        body.addWidget(self._about_card())
        body.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(content)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(10)
        root.addWidget(scroll, 1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        btn_cancel = QPushButton(tr("取消"))
        btn_ok = QPushButton(tr("保存"))
        btn_ok.setProperty("role", "primary")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._save)
        footer.addWidget(btn_cancel)
        footer.addWidget(btn_ok)
        root.addLayout(footer)

        self._refresh_versions()
        self._refresh_menu_state()

    # ---------- 卡片 ----------
    def _language_card(self) -> QWidget:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(9)
        layout.addWidget(section_label(tr("界面语言")))
        row = QHBoxLayout()
        row.setSpacing(10)
        self.combo_lang = QComboBox()
        self.combo_lang.addItem(f'{tr("跟随系统")} ({LANGUAGES[resolve(AUTO)]})', AUTO)
        for code, name in LANGUAGES.items():
            self.combo_lang.addItem(name, code)
        idx = self.combo_lang.findData(self.settings.language)
        self.combo_lang.setCurrentIndex(max(0, idx))
        self.combo_lang.setFixedWidth(240)
        row.addWidget(self.combo_lang)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(hint_label(tr("切换后需要重启程序才会生效。")))
        return card

    def _tools_card(self) -> QWidget:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(9)
        layout.addWidget(section_label(tr("工具链目录")))
        layout.addWidget(hint_label(tr("存放 cjxl / avifenc / cwebp / oxipng 的目录，程序会递归查找这些 exe。默认使用程序目录下的 tools\\bin。")))

        row = QHBoxLayout()
        row.setSpacing(6)
        self.edit_tools = QLineEdit()
        self.edit_tools.setPlaceholderText(str(paths.default_tools_root() or tr("未指定，使用程序目录下的 tools\\bin")))
        self.edit_tools.setText(self.settings.tools_root or "")
        btn_browse = QPushButton(tr("浏览…"))
        btn_reset = QPushButton(tr("恢复默认"))
        btn_recheck = QPushButton(tr("重新检测"))
        btn_browse.clicked.connect(self._browse)
        btn_reset.clicked.connect(lambda: self.edit_tools.setText(""))
        btn_recheck.clicked.connect(self._reload_tools)
        row.addWidget(self.edit_tools, 1)
        row.addWidget(btn_browse)
        row.addWidget(btn_recheck)
        row.addWidget(btn_reset)
        layout.addLayout(row)

        self.version_grid = QGridLayout()
        self.version_grid.setHorizontalSpacing(16)
        self.version_grid.setVerticalSpacing(5)
        self.version_grid.setContentsMargins(0, 0, 10, 0)
        self.version_grid.setColumnMinimumWidth(0, 96)
        self.version_grid.setColumnStretch(1, 1)
        self.version_grid.setColumnMinimumWidth(2, 118)
        layout.addLayout(self.version_grid)
        return card

    def _output_card(self) -> QWidget:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(9)
        layout.addWidget(section_label(tr("输出")))
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(field_label(tr("输出位置")))
        placeholder = QLabel(tr("与源文件同目录（原名 + 新扩展名）"))
        placeholder.setObjectName("Hint")
        row.addWidget(placeholder)
        row.addStretch(1)
        layout.addLayout(row)

        row2 = QHBoxLayout()
        row2.setSpacing(10)
        row2.addWidget(field_label(tr("重名处理")))
        self.combo_policy = QComboBox()
        for key, label in POLICY_LABEL.items():
            self.combo_policy.addItem(tr(label), key)
        idx = self.combo_policy.findData(self.settings.policy)
        self.combo_policy.setCurrentIndex(max(0, idx))
        self.combo_policy.setFixedWidth(240)
        row2.addWidget(self.combo_policy)
        row2.addStretch(1)
        layout.addLayout(row2)
        layout.addWidget(hint_label(tr("原文件始终保留；输出文件名与源文件同名时按此规则处理。")))
        return card

    def _menu_card(self) -> QWidget:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(9)
        layout.addWidget(section_label(tr("右键菜单")))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.menu_state = QLabel("")
        self.menu_state.setObjectName("Hint")
        self.btn_install = QPushButton(tr("注册右键菜单"))
        self.btn_uninstall = QPushButton(tr("移除"))
        self.btn_install.setProperty("role", "primary")
        self.btn_install.clicked.connect(self._install_menu)
        self.btn_uninstall.clicked.connect(self._uninstall_menu)
        row.addWidget(self.menu_state, 1)
        row.addWidget(self.btn_install)
        row.addWidget(self.btn_uninstall)
        layout.addLayout(row)
        layout.addWidget(
            hint_label(
                tr(
                    "注册写入 HKEY_CURRENT_USER，不需要管理员权限；覆盖 jpg/png/webp/bmp/tif/gif/avif/jxl 等扩展名，"
                    "支持一次选中多个文件批量加入工作区。Windows 11 会把此类菜单收纳到「显示更多选项」中。"
                )
            )
        )
        return card

    def _about_card(self) -> QWidget:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(7)
        layout.addWidget(section_label(tr("关于")))
        line = QLabel(tr("ImgPress {version} · 本地离线运行，不上传任何图片", version=paths.APP_VERSION))
        line.setObjectName("Hint")
        layout.addWidget(line)

        lic = QLabel(
            f'{tr("以 MIT 许可证开源，欢迎 issue 与 PR。")}&nbsp;&nbsp;'
            f'<a href="{paths.PROJECT_URL}" style="color:{theme.ACCENT}; text-decoration:none;">'
            f'GitHub · syj150/ImgPress</a>'
        )
        lic.setObjectName("Hint")
        lic.setTextFormat(Qt.RichText)
        lic.setOpenExternalLinks(True)
        lic.setCursor(Qt.PointingHandCursor)
        lic.setToolTip(paths.PROJECT_URL)
        layout.addWidget(lic)
        chain = QLabel(" · ".join(CODEC_ENGINE[c] for c in CODECS))
        chain.setObjectName("Hint")
        chain.setWordWrap(True)
        layout.addWidget(chain)
        return card

    # ---------- 行为 ----------
    def _browse(self) -> None:
        start = self.edit_tools.text().strip() or str(paths.default_tools_root() or Path.home())
        folder = QFileDialog.getExistingDirectory(self, "选择工具链目录", start)
        if folder:
            self.edit_tools.setText(folder)
            self._reload_tools()

    def _current_tools(self) -> Toolchain:
        text = self.edit_tools.text().strip()
        root = Path(text) if text else paths.default_tools_root()
        return tools_mod.load(root)

    def _reload_tools(self) -> None:
        self.tools = self._current_tools()
        self._refresh_versions()

    def _refresh_versions(self) -> None:
        self.edit_tools.setToolTip(str(self.tools.root) if self.tools.root else "未指定，使用程序目录下的 tools\\bin")
        while self.version_grid.count():
            item = self.version_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        names = [
            ("cjxl", "JPEG XL 编码"),
            ("djxl", "JXL 解码"),
            ("avifenc", "AVIF 编码"),
            ("avifdec", "AVIF 解码"),
            ("cwebp", "WebP 编码"),
            ("dwebp", "WebP 解码"),
            ("oxipng", "PNG 优化"),
            ("ssimulacra2", "质量评分"),
        ]
        row = 0
        for key, label in names:
            path = self.tools.get(key)
            name_label = QLabel(tr(label))
            name_label.setObjectName("FieldLabel")
            ver = QLabel(self.tools.version(key) if path else tr("未找到"))
            ver.setObjectName("Mono")
            if not path:
                ver.setStyleSheet("QLabel{color:%s;}" % theme.ERR)
            self.version_grid.addWidget(name_label, row, 0)
            self.version_grid.addWidget(ver, row, 1)
            self.version_grid.addWidget(QLabel(f"{key}.exe"), row, 2)
            row += 1
        self.version_grid.setColumnStretch(1, 1)
        if not self.tools.paths:
            msg = QLabel(tr("工具目录无效：四个编码器都不可用，无法开始压缩。"))
            msg.setStyleSheet("QLabel{color:%s;}" % theme.ERR)
            self.version_grid.addWidget(msg, row, 0, 1, 3)

    def _refresh_menu_state(self) -> None:
        self.menu_state.setText(registry.status_text())
        installed = registry.is_installed()
        self.btn_install.setEnabled(not installed)
        self.btn_uninstall.setEnabled(installed or registry.current_target() is not None)

    def _launch_spec(self) -> tuple[Path, Path | None]:
        import sys

        if paths.is_frozen():
            return Path(sys.executable), None
        exe = Path(sys.executable).with_name("pythonw.exe")
        script = paths.app_dir() / "main.py"
        return exe, script

    def _install_menu(self) -> None:
        exe, script = self._launch_spec()
        try:
            count = registry.install(exe, script)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, tr("注册失败"), str(exc))
            return
        if count == 0:
            QMessageBox.warning(self, tr("注册失败"), tr("未能写入注册表，请检查权限或安全软件拦截。"))
        self._refresh_menu_state()

    def _uninstall_menu(self) -> None:
        registry.uninstall()
        self._refresh_menu_state()

    def _save(self) -> None:
        text = self.edit_tools.text().strip()
        self.settings.tools_root = str(Path(text)) if text else None
        self.settings.policy = self.combo_policy.currentData()

        old_lang = self._initial_language
        new_lang = self.combo_lang.currentData()
        self.settings.language = new_lang
        self.applied.emit()
        self.accept()

        if resolve(old_lang) != resolve(new_lang):
            reply = QMessageBox.question(
                self,
                tr("界面语言"),
                tr("语言已切换，重启后生效。现在重启吗？"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                self._restart()

    @staticmethod
    def _restart() -> None:
        """重启自身。开发模式下带上入口脚本。"""
        import sys

        from PySide6.QtCore import QProcess
        from PySide6.QtWidgets import QApplication

        program = sys.executable
        args = [] if paths.is_frozen() else [str(paths.app_dir() / "main.py")]
        QProcess.startDetached(program, args)
        QApplication.quit()
