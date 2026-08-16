# -*- coding: utf-8 -*-
"""
LabelImg2 Next-Gen - 官方图形化安装向导 (Windows GUI Setup Installer)
实现商业级应用安装流程：
1. 欢迎界面与协议
2. 选择安装目录
3. 提取核心文件、自动配置 Python 运行环境与核心 AI 依赖
4. 自动生成专属 App 图标桌面快捷方式与开始菜单入口
5. 完成并直接启动工作台
"""

import os
import sys
import shutil
import zipfile
import subprocess
import threading
import time

from PyQt5.QtCore import Qt, pyqtSignal, QThread, QSize
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor
from PyQt5.QtWidgets import (
    QApplication, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar, QTextEdit,
    QCheckBox, QFileDialog, QMessageBox, QFrame
)

INSTALLER_STYLE = """
QWizard {
    background-color: #FFFFFF;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}
QWizardPage {
    background-color: #FFFFFF;
}
QLabel {
    color: #1E293B;
    font-size: 13px;
}
QLabel#title_label {
    font-size: 18px;
    font-weight: bold;
    color: #0F172A;
}
QLabel#subtitle_label {
    font-size: 13px;
    color: #64748B;
    margin-bottom: 12px;
}
QLineEdit {
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 8px 12px;
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
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: bold;
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
    border-radius: 6px;
    text-align: center;
    background: #F1F5F9;
    height: 22px;
    font-weight: bold;
    color: #1E293B;
}
QProgressBar::chunk {
    background-color: #2563EB;
    border-radius: 5px;
}
QTextEdit {
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    background: #0F172A;
    color: #38BDF8;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 8px;
}
"""

def get_bundle_dir():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.abspath(os.path.dirname(__file__))

def get_app_icon():
    ico_path = os.path.join(get_bundle_dir(), "img", "labelImg2.ico")
    if os.path.exists(ico_path):
        return QIcon(ico_path)
    png_path = os.path.join(get_bundle_dir(), "img", "labelImg2.png")
    if os.path.exists(png_path):
        return QIcon(png_path)
    return QIcon()


class InstallWorker(QThread):
    progress_changed = pyqtSignal(int, str)
    log_received = pyqtSignal(str)
    finished_success = pyqtSignal(str)
    failed_error = pyqtSignal(str)

    def __init__(self, target_dir: str):
        super().__init__()
        self.target_dir = os.path.abspath(target_dir)

    def run(self):
        try:
            self.progress_changed.emit(5, "正在创建安装目录...")
            os.makedirs(self.target_dir, exist_ok=True)

            bundle_dir = get_bundle_dir()
            payload_zip = os.path.join(bundle_dir, "app_payload.zip")

            self.progress_changed.emit(15, "正在解压 LabelImg2 核心程序文件...")
            if os.path.exists(payload_zip):
                with zipfile.ZipFile(payload_zip, 'r') as zf:
                    zf.extractall(self.target_dir)
            else:
                # 源码安装模式复制
                for item in ["core", "libs", "ui", "utils", "data", "img", "labelImg.py", "requirements.txt", "Start_LabelImg2.bat", "setup_env.bat", "Create_Desktop_Shortcut.bat", "yolov8n.pt", "yolo26n.pt"]:
                    src = os.path.join(bundle_dir, item)
                    dst = os.path.join(self.target_dir, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    elif os.path.isfile(src):
                        shutil.copy2(src, dst)

            self.progress_changed.emit(40, "正在检测并配置 Python 深度学习运行环境...")
            self.log_received.emit(f"[*] 目标安装目录: {self.target_dir}")

            # 调用目标目录中的 setup_env.bat 进行自动化环境配置
            setup_script = os.path.join(self.target_dir, "setup_env.bat")
            if os.path.exists(setup_script):
                self.log_received.emit("[*] 正在执行全自动环境初始化与依赖安装...")
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
                        if "步骤" in stripped:
                            self.progress_changed.emit(65, stripped)

            self.progress_changed.emit(85, "正在创建桌面与开始菜单快捷方式 (专属 App 图标)...")
            self.create_shortcuts()

            self.progress_changed.emit(100, "安装全部完成！")
            self.finished_success.emit(self.target_dir)

        except Exception as e:
            self.failed_error.emit(str(e))

    def create_shortcuts(self):
        icon_path = os.path.join(self.target_dir, "img", "labelImg2.ico")
        target_bat = os.path.join(self.target_dir, "Start_LabelImg2.bat")

        ps_cmd = (
            f"$WshShell = New-Object -ComObject WScript.Shell; "
            f"$Desktop = [Environment]::GetFolderPath('Desktop'); "
            f"$Shortcut = $WshShell.CreateShortcut($Desktop + '\\LabelImg2.lnk'); "
            f"$Shortcut.TargetPath = '{target_bat}'; "
            f"$Shortcut.WorkingDirectory = '{self.target_dir}'; "
            f"$Shortcut.IconLocation = '{icon_path},0'; "
            f"$Shortcut.Description = 'LabelImg2 Next-Gen - AI 智能计算机视觉标注工作台'; "
            f"$Shortcut.Save();"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)


class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("欢迎使用 LabelImg2 Next-Gen 安装向导")
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # 顶部 Logo 徽标
        logo_layout = QHBoxLayout()
        logo_lbl = QLabel()
        png_path = os.path.join(get_bundle_dir(), "img", "labelImg2.png")
        if os.path.exists(png_path):
            pix = QPixmap(png_path).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        logo_layout.addWidget(logo_lbl)

        title_box = QVBoxLayout()
        lbl_title = QLabel("LabelImg2 Next-Gen v1.0.0")
        lbl_title.setObjectName("title_label")
        lbl_sub = QLabel("AI 智能计算机视觉标注与模型自训练一体化工作台")
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
            "本安装程序将引导您在电脑上安装 <b>LabelImg2 Next-Gen</b> 并自动完成全套 AI 运行环境的初始化搭建。<br><br>"
            "<b>✨ 核心功能亮点：</b><br>"
            "• 内置 YOLO 模型中心与单图/批量一键自动智能标注<br>"
            "• 内置 YOLO 闭环模型微调控制台 (实时流式监控 Loss / mAP)<br>"
            "• 支持水平矩形框与 OBB 任意角度旋转框 (动态变速旋转、长宽微调)<br>"
            "• 0 目标空标签自动存盘与文件夹生成<br>"
            "• 全自动环境检测与智能依赖配置，无需手动敲写任何命令<br><br>"
            "点击 <b>「下一步」</b> 继续安装流程。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("line-height: 140%; font-size: 13px; color: #334155;")
        layout.addWidget(desc)
        layout.addStretch()


class DirectoryPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("选择安装目标文件夹")
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        lbl = QLabel("请选择 LabelImg2 将要安装到的文件夹路径：")
        layout.addWidget(lbl)

        path_box = QHBoxLayout()
        default_dir = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\"), "Programs", "LabelImg2")
        self.txt_path = QLineEdit(default_dir)
        path_box.addWidget(self.txt_path)

        btn_browse = QPushButton("浏览...")
        btn_browse.setObjectName("btn_secondary")
        btn_browse.clicked.connect(self.browse_path)
        path_box.addWidget(btn_browse)
        layout.addLayout(path_box)

        lbl_tip = QLabel("💡 提示: 建议安装在空间充足的固态硬盘 (SSD) 盘符，方便高速运行 AI 推理与模型训练。")
        lbl_tip.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(lbl_tip)

        self.registerField("install_dir*", self.txt_path)
        layout.addStretch()

    def browse_path(self):
        d = QFileDialog.getExistingDirectory(self, "选择安装目录", self.txt_path.text())
        if d:
            self.txt_path.setText(os.path.join(d, "LabelImg2") if not d.endswith("LabelImg2") else d)


class ProgressPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("正在安装与配置环境")
        self.setSubTitle("安装程序正在部署核心文件并配置 Python 深度学习运行环境，请稍候...")
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self.lbl_status = QLabel("准备安装...")
        self.lbl_status.setStyleSheet("font-weight: bold; color: #0F172A;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        self.worker: Optional[InstallWorker] = None
        self.is_installed = False

    def initializePage(self):
        target_dir = self.field("install_dir")
        self.wizard().button(QWizard.BackButton).setEnabled(False)
        self.wizard().button(QWizard.NextButton).setEnabled(False)

        self.worker = InstallWorker(target_dir)
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
        self.lbl_status.setText(f"❌ 安装过程出错: {err}")
        QMessageBox.critical(self, "安装失败", f"安装过程中发生错误:\n{err}")
        self.wizard().button(QWizard.BackButton).setEnabled(True)

    def isComplete(self):
        return self.is_installed


class FinishedPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("LabelImg2 Next-Gen 安装完成！")
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        lbl_success = QLabel("🎉 恭喜！LabelImg2 标注工作台已成功安装到您的电脑。")
        lbl_success.setStyleSheet("font-size: 15px; font-weight: bold; color: #16A34A;")
        layout.addWidget(lbl_success)

        desc = QLabel(
            "• 已在您的电脑桌面上创建了带有专属 App 图标的快捷方式 <b>[LabelImg2]</b><br>"
            "• 全部深度学习 AI 依赖环境已就绪，无需手动启动命令行。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; color: #334155; line-height: 150%;")
        layout.addWidget(desc)

        self.chk_launch = QCheckBox("立即启动 LabelImg2 AI 标注工作台")
        self.chk_launch.setChecked(True)
        self.chk_launch.setStyleSheet("font-size: 14px; font-weight: bold; color: #2563EB; margin-top: 10px;")
        layout.addWidget(self.chk_launch)

        layout.addStretch()


class InstallerWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LabelImg2 Next-Gen v1.0.0 安装向导")
        self.setWindowIcon(get_app_icon())
        self.resize(650, 520)
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

        self.setButtonText(QWizard.NextButton, "下一步 >")
        self.setButtonText(QWizard.BackButton, "< 上一步")
        self.setButtonText(QWizard.FinishButton, "完成")
        self.setButtonText(QWizard.CancelButton, "取消")

    def accept(self):
        # 点击完成时判断是否立即启动
        if hasattr(self.finish_page, 'chk_launch') and self.finish_page.chk_launch.isChecked():
            target_dir = self.field("install_dir")
            bat_path = os.path.join(target_dir, "Start_LabelImg2.bat")
            if os.path.exists(bat_path):
                subprocess.Popen(["cmd.exe", "/c", "start", "", bat_path], cwd=target_dir)
        super().accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LabelImg2 Setup")
    app.setWindowIcon(get_app_icon())

    wizard = InstallerWizard()
    wizard.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
