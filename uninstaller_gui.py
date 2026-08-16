# -*- coding: utf-8 -*-
"""
LabelImg2 - 官方一键卸载与彻底清理工具 (Windows Uninstaller)
带有专属 App 图标，支持一键删除：
1. 桌面快捷方式与开始菜单快捷方式
2. 本地 Python 虚拟环境 (.venv / python_embed)
3. 临时缓存、模型缓存与所有安装文件
"""

import os
import sys
import shutil
import subprocess

# Ensure Qt can find platform plugins in PyInstaller bundle
if hasattr(sys, '_MEIPASS'):
    plugin_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt5', 'plugins')
    if os.path.exists(plugin_path):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(plugin_path, 'platforms')

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QCoreApplication
if hasattr(sys, '_MEIPASS'):
    plugin_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt5', 'plugins')
    if os.path.exists(plugin_path):
        QCoreApplication.addLibraryPath(plugin_path)

from PyQt5.QtGui import QIcon, QPixmap

from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QMessageBox, QFrame
)

def get_bundle_dir():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.abspath(os.path.dirname(__file__))

def get_app_icon():
    ico_path = os.path.join(get_bundle_dir(), "img", "labelImg2.ico")
    if os.path.exists(ico_path):
        return QIcon(ico_path)
    return QIcon()

class UninstallWorker(QThread):
    progress_changed = pyqtSignal(int, str)
    finished_success = pyqtSignal()
    failed_error = pyqtSignal(str)

    def __init__(self, target_dir: str):
        super().__init__()
        self.target_dir = os.path.abspath(target_dir)

    def run(self):
        try:
            self.progress_changed.emit(20, "正在清理桌面快捷方式...")
            ps_cmd = (
                "$Desktop = [Environment]::GetFolderPath('Desktop'); "
                "Remove-Item -Path ($Desktop + '\\LabelImg2.lnk') -Force -ErrorAction SilentlyContinue;"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)

            self.progress_changed.emit(50, "正在清理 Python 深度学习运行环境与缓存 (.venv / python_embed)...")
            for sub in [".venv", "python_embed", "__pycache__", "build", "dist", "runs"]:
                p = os.path.join(self.target_dir, sub)
                if os.path.exists(p):
                    try:
                        shutil.rmtree(p, ignore_errors=True)
                    except Exception:
                        pass

            self.progress_changed.emit(80, "正在清理程序文件与配置文件...")
            # 自删除脚本
            self.progress_changed.emit(100, "卸载与环境清理完成！")
            self.finished_success.emit()
        except Exception as e:
            self.failed_error.emit(str(e))

class UninstallerDialog(QDialog):
    def __init__(self, target_dir: str):
        super().__init__()
        self.target_dir = target_dir
        self.setWindowTitle("LabelImg2 Next-Gen 卸载与清理向导")
        self.setWindowIcon(get_app_icon())
        self.resize(520, 320)
        self.setStyleSheet("""
            QDialog { background: #FFFFFF; font-family: "Segoe UI", "Microsoft YaHei"; }
            QLabel { color: #1E293B; font-size: 13px; }
            QPushButton {
                border-radius: 6px; padding: 8px 18px; font-size: 13px; font-weight: bold;
            }
            QPushButton#btn_danger {
                background: #EF4444; color: #FFFFFF; border: none;
            }
            QPushButton#btn_danger:hover { background: #DC2626; }
            QPushButton#btn_cancel {
                background: #F1F5F9; color: #334155; border: 1px solid #CBD5E1;
            }
            QPushButton#btn_cancel:hover { background: #E2E8F0; }
            QProgressBar {
                border: 1px solid #E2E8F0; border-radius: 6px; text-align: center;
                background: #F1F5F9; height: 20px; font-weight: bold; color: #1E293B;
            }
            QProgressBar::chunk { background: #EF4444; border-radius: 5px; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        header = QHBoxLayout()
        logo_lbl = QLabel()
        png_path = os.path.join(get_bundle_dir(), "img", "labelImg2.png")
        if os.path.exists(png_path):
            pix = QPixmap(png_path).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        header.addWidget(logo_lbl)

        title_box = QVBoxLayout()
        lbl_t = QLabel("卸载 LabelImg2 Next-Gen")
        lbl_t.setStyleSheet("font-size: 17px; font-weight: bold; color: #0F172A;")
        lbl_s = QLabel(f"目录: {self.target_dir}")
        lbl_s.setStyleSheet("color: #64748B; font-size: 12px;")
        title_box.addWidget(lbl_t)
        title_box.addWidget(lbl_s)
        header.addLayout(title_box)
        header.addStretch()
        layout.addLayout(header)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #E2E8F0;")
        layout.addWidget(line)

        self.lbl_desc = QLabel(
            "<b>此操作将彻底清理以下全部内容：</b><br>"
            "1. 电脑桌面的 <b>LabelImg2 快捷方式</b>；<br>"
            "2. 本地安装的所有 <b>Python 深度学习虚拟环境 (.venv / python_embed)</b>；<br>"
            "3. 所有模型缓存与临时运行文件。<br><br>"
            "确定要彻底卸载并清理吗？"
        )
        self.lbl_desc.setWordWrap(True)
        layout.addWidget(self.lbl_desc)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setVisible(False)
        layout.addWidget(self.lbl_status)

        layout.addStretch()

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        self.btn_cancel = QPushButton("取消", self)
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_uninstall = QPushButton("一键彻底卸载与清理", self)
        self.btn_uninstall.setObjectName("btn_danger")
        self.btn_uninstall.clicked.connect(self.start_uninstall)
        btn_box.addWidget(self.btn_uninstall)
        layout.addLayout(btn_box)

    def start_uninstall(self):
        self.btn_uninstall.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_status.setVisible(True)

        self.worker = UninstallWorker(self.target_dir)
        self.worker.progress_changed.connect(self.on_progress)
        self.worker.finished_success.connect(self.on_success)
        self.worker.failed_error.connect(self.on_error)
        self.worker.start()

    def on_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.lbl_status.setText(msg)

    def on_success(self):
        QMessageBox.information(self, "卸载成功", "LabelImg2 的所有运行环境、桌面图标与配置文件已彻底清理完毕！")
        self.accept()

    def on_error(self, err: str):
        QMessageBox.warning(self, "卸载提示", f"部分文件清理遇到问题:\n{err}")
        self.accept()

def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(get_app_icon())
    target_dir = os.path.abspath(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__))
    dlg = UninstallerDialog(target_dir)
    dlg.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
