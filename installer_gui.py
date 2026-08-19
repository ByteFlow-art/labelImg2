# -*- coding: utf-8 -*-
"""
LabelImg2 - 官方图形化安装程序 (Windows Setup Installer)
企业级向导流程：
1. 欢迎与许可协议 (Welcome & License Agreement)
2. 安装目录与快捷方式配置 (Destination Folder & Options)
3. 核心文件部署与环境初始化 (Installation & Environment Setup)
4. 安装完成与即刻启动 (Completion & Launch)
"""

import os
import sys
import shutil
import zipfile
import subprocess

if hasattr(sys, '_MEIPASS'):
    plugin_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt5', 'plugins')
    if os.path.exists(plugin_path):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(plugin_path, 'platforms')

from PyQt5.QtCore import Qt, pyqtSignal, QThread, QCoreApplication
if hasattr(sys, '_MEIPASS'):
    plugin_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt5', 'plugins')
    if os.path.exists(plugin_path):
        QCoreApplication.addLibraryPath(plugin_path)

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar, QTextEdit,
    QCheckBox, QFileDialog, QMessageBox, QFrame, QGroupBox
)

INSTALLER_STYLE = """
QWizard {
    background-color: #FFFFFF;
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
}
QWizardPage {
    background-color: #FFFFFF;
}
QLabel {
    color: #1E293B;
    font-size: 13px;
}
QLabel#title_label {
    font-size: 17px;
    font-weight: bold;
    color: #0F172A;
}
QLabel#subtitle_label {
    font-size: 12px;
    color: #64748B;
}
QLineEdit {
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 13px;
    background: #F8FAFC;
    color: #0F172A;
}
QLineEdit:focus {
    border: 1.5px solid #2563EB;
    background: #FFFFFF;
}
QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 7px 18px;
    font-size: 13px;
    font-weight: 600;
    min-width: 75px;
}
QPushButton:hover {
    background-color: #1D4ED8;
}
QPushButton:pressed {
    background-color: #1E40AF;
}
QPushButton#btn_secondary {
    background-color: #F1F5F9;
    color: #334155;
    border: 1px solid #CBD5E1;
}
QPushButton#btn_secondary:hover {
    background-color: #E2E8F0;
}
QProgressBar {
    border: 1px solid #E2E8F0;
    border-radius: 4px;
    text-align: center;
    background: #F1F5F9;
    height: 20px;
    font-size: 12px;
    font-weight: bold;
    color: #1E293B;
}
QProgressBar::chunk {
    background-color: #2563EB;
    border-radius: 3px;
}
QTextEdit {
    border: 1px solid #E2E8F0;
    border-radius: 4px;
    background: #0F172A;
    color: #38BDF8;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 11px;
    padding: 6px;
}
QGroupBox {
    font-size: 13px;
    font-weight: bold;
    color: #334155;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QCheckBox {
    font-size: 13px;
    color: #334155;
}
"""

def get_bundle_dir():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.abspath(os.path.dirname(__file__))

def get_app_icon():
    for ico_name in ["app.ico", "labelImg2.ico"]:
        ico_path = os.path.join(get_bundle_dir(), "img", ico_name)
        if os.path.exists(ico_path):
            return QIcon(ico_path)
    for png_name in ["app.png", "labelImg2.png"]:
        png_path = os.path.join(get_bundle_dir(), "img", png_name)
        if os.path.exists(png_path):
            return QIcon(png_path)
    return QIcon()


class InstallWorker(QThread):
    progress_changed = pyqtSignal(int, str)
    log_received = pyqtSignal(str)
    finished_success = pyqtSignal(str)
    failed_error = pyqtSignal(str)

    def __init__(self, target_dir: str, create_desktop_shortcut: bool, auto_setup_env: bool):
        super().__init__()
        self.target_dir = os.path.abspath(target_dir)
        self.create_desktop_shortcut = create_desktop_shortcut
        self.auto_setup_env = auto_setup_env

    def run(self):
        try:
            self.progress_changed.emit(5, "正在创建安装目录...")
            os.makedirs(self.target_dir, exist_ok=True)

            bundle_dir = get_bundle_dir()
            payload_zip = os.path.join(bundle_dir, "app_payload.zip")

            self.progress_changed.emit(15, "正在提取应用程序组件...")
            if os.path.exists(payload_zip):
                with zipfile.ZipFile(payload_zip, 'r') as zf:
                    zf.extractall(self.target_dir)
            else:
                for item in ["core", "libs", "ui", "utils", "data", "img", "labelImg.py", "requirements.txt", "Start_LabelImg2.bat", "setup_env.bat", "Create_Desktop_Shortcut.bat", "yolov8n.pt", "yolo26n.pt"]:
                    src = os.path.join(bundle_dir, item)
                    dst = os.path.join(self.target_dir, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    elif os.path.isfile(src):
                        shutil.copy2(src, dst)

            if self.auto_setup_env:
                self.progress_changed.emit(40, "正在检测并配置 Python 运行环境...")
                self.log_received.emit(f"[*] 目标安装路径: {self.target_dir}")

                setup_script = os.path.join(self.target_dir, "setup_env.bat")
                if os.path.exists(setup_script):
                    self.log_received.emit("[*] 正在执行全自动环境检测与依赖项部署...")
                    p = subprocess.Popen(
                        ["cmd.exe", "/c", setup_script, "--auto"],
                        cwd=self.target_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    while True:
                        line = p.stdout.readline()
                        if not line and p.poll() is not None:
                            break
                        if line:
                            stripped = line.strip()
                            self.log_received.emit(stripped)
                            if "步骤" in stripped or "安装" in stripped:
                                self.progress_changed.emit(70, stripped)

            if self.create_desktop_shortcut:
                self.progress_changed.emit(85, "正在创建桌面快捷方式...")
                self.create_shortcuts()

            self.progress_changed.emit(100, "安装全部完成！")
            self.finished_success.emit(self.target_dir)

        except Exception as e:
            self.failed_error.emit(str(e))

    def create_shortcuts(self):
        icon_path = os.path.join(self.target_dir, "img", "app.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(self.target_dir, "img", "labelImg2.ico")
        target_bat = os.path.join(self.target_dir, "Start_LabelImg2.bat")

        ps_cmd = (
            f"$WshShell = New-Object -ComObject WScript.Shell; "
            f"$Desktop = [Environment]::GetFolderPath('Desktop'); "
            f"$Shortcut = $WshShell.CreateShortcut($Desktop + '\\LabelImg2.lnk'); "
            f"$Shortcut.TargetPath = '{target_bat}'; "
            f"$Shortcut.WorkingDirectory = '{self.target_dir}'; "
            f"$Shortcut.IconLocation = '{icon_path},0'; "
            f"$Shortcut.Description = 'LabelImg2 - AI 目标检测标注与模型自训练工作台'; "
            f"$Shortcut.Save();"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)


class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("欢迎使用 LabelImg2 安装向导")
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        logo_layout = QHBoxLayout()
        logo_lbl = QLabel()
        png_path = os.path.join(get_bundle_dir(), "img", "app.png")
        if not os.path.exists(png_path):
            png_path = os.path.join(get_bundle_dir(), "img", "labelImg2.png")
        if os.path.exists(png_path):
            pix = QPixmap(png_path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        logo_layout.addWidget(logo_lbl)

        title_box = QVBoxLayout()
        lbl_title = QLabel("LabelImg2 v1.0.0")
        lbl_title.setObjectName("title_label")
        lbl_sub = QLabel("深度学习目标检测标注与模型自训练一体化工作台")
        lbl_sub.setObjectName("subtitle_label")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        logo_layout.addLayout(title_box)
        logo_layout.addStretch()
        layout.addLayout(logo_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #E2E8F0;")
        layout.addWidget(line)

        desc = QLabel(
            "本安装程序将在您的计算机上安装 <b>LabelImg2</b> 并初始化所需运行环境。<br><br>"
            "建议在继续之前关闭其他无关应用程序。<br><br>"
            "本软件遵循开源 MIT 许可证发布，供学术研究与工业生产免费使用。<br><br>"
            "点击 <b>「下一步」</b> 继续安装。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; color: #334155; line-height: 160%;")
        layout.addWidget(desc)

        layout.addStretch()
        self.chk_agree = QCheckBox("我接受许可协议条款 (MIT License)")
        self.chk_agree.setChecked(True)
        self.chk_agree.stateChanged.connect(self.completeChanged)
        layout.addWidget(self.chk_agree)

    def isComplete(self):
        return self.chk_agree.isChecked()


class DirectoryPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("选择安装目标位置")
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        lbl = QLabel("请指定 LabelImg2 将要安装到的目标文件夹：")
        layout.addWidget(lbl)

        path_box = QHBoxLayout()
        default_dir = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\"), "Programs", "LabelImg2")
        self.txt_path = QLineEdit(default_dir)
        path_box.addWidget(self.txt_path)

        btn_browse = QPushButton("浏览(B)...")
        btn_browse.setObjectName("btn_secondary")
        btn_browse.clicked.connect(self.browse_path)
        path_box.addWidget(btn_browse)
        layout.addLayout(path_box)

        # 选项配置组
        opt_group = QGroupBox("安装选项")
        opt_layout = QVBoxLayout(opt_group)
        opt_layout.setSpacing(8)

        self.chk_shortcut = QCheckBox("创建桌面快捷方式")
        self.chk_shortcut.setChecked(True)
        opt_layout.addWidget(self.chk_shortcut)

        self.chk_setup_env = QCheckBox("自动检测并配置 Python 深度学习运行环境")
        self.chk_setup_env.setChecked(True)
        opt_layout.addWidget(self.chk_setup_env)

        layout.addWidget(opt_group)

        self.registerField("install_dir*", self.txt_path)
        layout.addStretch()

    def browse_path(self):
        d = QFileDialog.getExistingDirectory(self, "选择安装目录", self.txt_path.text())
        if d:
            self.txt_path.setText(os.path.join(d, "LabelImg2") if not d.endswith("LabelImg2") else d)


class ProgressPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("正在安装 LabelImg2")
        self.setSubTitle("安装向导正在部署文件并初始化环境，请稍候...")
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self.lbl_status = QLabel("正在准备安装...")
        self.lbl_status.setStyleSheet("font-weight: bold; color: #0F172A;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        self.worker = None
        self.is_installed = False

    def initializePage(self):
        target_dir = self.field("install_dir")
        chk_shortcut = self.wizard().dir_page.chk_shortcut.isChecked()
        chk_env = self.wizard().dir_page.chk_setup_env.isChecked()

        self.wizard().button(QWizard.BackButton).setEnabled(False)
        self.wizard().button(QWizard.NextButton).setEnabled(False)
        self.wizard().button(QWizard.CancelButton).setEnabled(False)

        self.worker = InstallWorker(target_dir, chk_shortcut, chk_env)
        self.worker.progress_changed.connect(self.on_progress)
        self.worker.log_received.connect(self.on_log)
        self.worker.finished_success.connect(self.on_success)
        self.worker.failed_error.connect(self.on_error)
        self.worker.start()

    def on_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.lbl_status.setText(msg)

    def on_log(self, text: str):
        self.log_view.append(text)

    def on_success(self, target_dir: str):
        self.is_installed = True
        self.wizard().button(QWizard.NextButton).setEnabled(True)
        self.wizard().next()

    def on_error(self, err: str):
        self.lbl_status.setText(f"安装过程出错: {err}")
        QMessageBox.critical(self, "安装失败", f"安装过程中发生错误:\n{err}")
        self.wizard().button(QWizard.BackButton).setEnabled(True)
        self.wizard().button(QWizard.CancelButton).setEnabled(True)

    def isComplete(self):
        return self.is_installed


class FinishedPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("LabelImg2 安装向导完成")
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        lbl_success = QLabel("LabelImg2 已成功安装到您的计算机。")
        lbl_success.setStyleSheet("font-size: 15px; font-weight: bold; color: #16A34A;")
        layout.addWidget(lbl_success)

        desc = QLabel(
            "您可以通过桌面快捷方式随时启动 <b>LabelImg2</b> 工作台。<br><br>"
            "点击 <b>「完成」</b> 按钮退出安装向导。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; color: #334155; line-height: 160%;")
        layout.addWidget(desc)

        self.chk_launch = QCheckBox("立即运行 LabelImg2 工作台")
        self.chk_launch.setChecked(True)
        self.chk_launch.setStyleSheet("font-size: 13px; font-weight: bold; color: #2563EB; margin-top: 12px;")
        layout.addWidget(self.chk_launch)

        layout.addStretch()


class InstallerWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LabelImg2 v1.0.0 安装程序")
        self.setWindowIcon(get_app_icon())
        self.resize(580, 440)
        self.setStyleSheet(INSTALLER_STYLE)
        self.setWizardStyle(QWizard.ModernStyle)

        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.setOption(QWizard.NoCancelButton, False)

        self.addPage(WelcomePage())
        self.dir_page = DirectoryPage()
        self.addPage(self.dir_page)
        self.addPage(ProgressPage())
        self.finish_page = FinishedPage()
        self.addPage(self.finish_page)

        self.setButtonText(QWizard.NextButton, "下一步(N) >")
        self.setButtonText(QWizard.BackButton, "< 上一步(B)")
        self.setButtonText(QWizard.FinishButton, "完成(F)")
        self.setButtonText(QWizard.CancelButton, "取消")

    def accept(self):
        if hasattr(self.finish_page, 'chk_launch') and self.finish_page.chk_launch.isChecked():
            target_dir = self.field("install_dir")
            bat_path = os.path.join(target_dir, "Start_LabelImg2.bat")
            if os.path.exists(bat_path):
                subprocess.Popen(["cmd.exe", "/c", "start", "", bat_path], cwd=target_dir)
        super().accept()


def main():
    try:
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)
        app.setApplicationName("LabelImg2 Setup")
        app.setWindowIcon(get_app_icon())

        wizard = InstallerWizard()
        wizard.show()
        sys.exit(app.exec_())
    except Exception as e:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, f"安装向导启动异常:\n{e}", "LabelImg2 Setup Error", 0x10)
        sys.exit(1)


if __name__ == "__main__":
    main()


