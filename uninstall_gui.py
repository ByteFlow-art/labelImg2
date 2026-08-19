# -*- coding: utf-8 -*-
"""
LabelImg2 - 官方图形化卸载程序 (Uninstall Wizard)
提供交互式选项：
1. 彻底删除（已确定以后不再使用）
2. 保留配置的环境（后期可能继续使用）
"""

import os
import sys
import shutil
import subprocess
import time

try:
    from PyQt5.QtCore import Qt, QCoreApplication
    from PyQt5.QtGui import QIcon, QPixmap, QFont
    from PyQt5.QtWidgets import (
        QApplication, QDialog, QVBoxLayout, QHBoxLayout,
        QLabel, QRadioButton, QButtonGroup, QPushButton,
        QMessageBox, QFrame, QGroupBox, QProgressBar
    )
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False

UNINSTALL_STYLE = """
QDialog {
    background-color: #FFFFFF;
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
}
QLabel {
    color: #1E293B;
    font-size: 13px;
}
QGroupBox {
    font-size: 13px;
    font-weight: bold;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 15px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QRadioButton {
    font-size: 13px;
    color: #334155;
    spacing: 8px;
}
QRadioButton:checked {
    font-weight: bold;
    color: #2563EB;
}
QPushButton {
    background-color: #EF4444;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
    min-width: 80px;
}
QPushButton:hover {
    background-color: #DC2626;
}
QPushButton:pressed {
    background-color: #B91C1C;
}
QPushButton#btn_cancel {
    background-color: #F1F5F9;
    color: #334155;
    border: 1px solid #CBD5E1;
}
QPushButton#btn_cancel:hover {
    background-color: #E2E8F0;
}
"""

class UninstallDialog(QDialog if HAS_PYQT else object):
    def __init__(self, target_dir: str):
        if not HAS_PYQT:
            return
        super().__init__()
        self.target_dir = os.path.abspath(target_dir)
        self.setWindowTitle("LabelImg2 软件卸载向导")
        self.resize(520, 360)
        self.setFixedSize(520, 360)
        self.setStyleSheet(UNINSTALL_STYLE)

        ico_path = os.path.join(self.target_dir, "img", "app.ico")
        if os.path.exists(ico_path):
            self.setWindowIcon(QIcon(ico_path))

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 头部 Logo 与 标题
        header_box = QHBoxLayout()
        lbl_logo = QLabel()
        png_path = os.path.join(self.target_dir, "img", "app.png")
        if os.path.exists(png_path):
            pix = QPixmap(png_path).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl_logo.setPixmap(pix)
        header_box.addWidget(lbl_logo)

        title_box = QVBoxLayout()
        lbl_title = QLabel("LabelImg2 软件卸载")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        lbl_sub = QLabel(f"正在准备从计算机中卸载 LabelImg2")
        lbl_sub.setStyleSheet("font-size: 12px; color: #64748B;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header_box.addLayout(title_box)
        header_box.addStretch()
        layout.addLayout(header_box)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #E2E8F0;")
        layout.addWidget(line)

        # 卸载模式选项组
        grp = QGroupBox("请选择您希望执行的卸载方式")
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(12)

        self.rb_keep_env = QRadioButton("保留配置的环境（后期可能继续使用）")
        self.rb_keep_env.setChecked(True)
        lbl_keep_tip = QLabel("  删除程序所有代码与桌面快捷方式，但保留已配置的 Python / AI 隔离环境，方便以后随时重新安装使用。")
        lbl_keep_tip.setWordWrap(True)
        lbl_keep_tip.setStyleSheet("font-size: 11px; color: #64748B; margin-left: 22px;")

        self.rb_full_delete = QRadioButton("彻底删除所有文件（已确定以后不再使用）")
        lbl_full_tip = QLabel("  完全删除程序代码、虚拟环境、模型缓存及桌面快捷方式，彻底释放磁盘空间。")
        lbl_full_tip.setWordWrap(True)
        lbl_full_tip.setStyleSheet("font-size: 11px; color: #64748B; margin-left: 22px;")

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.rb_keep_env, 1)
        self.mode_group.addButton(self.rb_full_delete, 2)

        grp_layout.addWidget(self.rb_keep_env)
        grp_layout.addWidget(lbl_keep_tip)
        grp_layout.addWidget(self.rb_full_delete)
        grp_layout.addWidget(lbl_full_tip)
        layout.addWidget(grp)

        layout.addStretch()

        # 底部操作按钮
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("取消")
        btn_cancel.setObjectName("btn_cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_uninstall = QPushButton("确认卸载")
        btn_uninstall.clicked.connect(self.do_uninstall)
        btn_box.addWidget(btn_uninstall)

        layout.addLayout(btn_box)

    def do_uninstall(self):
        is_full_delete = self.rb_full_delete.isChecked()
        mode_text = "【彻底删除所有文件】" if is_full_delete else "【保留配置的环境】"
        reply = QMessageBox.question(
            self,
            "确认卸载",
            f"您选择的卸载模式为: {mode_text}\n\n确定要立即开始卸载 LabelImg2 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            # 1. 删除桌面快捷方式
            self.remove_desktop_shortcut()

            # 2. 执行文件删除逻辑
            if is_full_delete:
                # 彻底删除整个安装目录 (通过临时自删除脚本)
                self.schedule_full_dir_deletion()
            else:
                # 保留 .venv 和 python_embed，删除其余所有代码与文件
                self.clean_program_files_keep_env()

            QMessageBox.information(
                self,
                "卸载完成",
                f"LabelImg2 已成功卸载！\n" + ("已彻底清除所有安装文件。" if is_full_delete else "已清理程序文件，并保留了 Python 隔离环境。")
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "卸载出错", f"卸载过程中发生错误: {e}")

    def remove_desktop_shortcut(self):
        try:
            ps_cmd = (
                "$d = [Environment]::GetFolderPath('Desktop'); "
                "$lnk = $d + '\\LabelImg2.lnk'; "
                "if (Test-Path $lnk) { Remove-Item -Force $lnk }"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
        except Exception:
            pass

    def clean_program_files_keep_env(self):
        """删除源码、配置与图标，但保留 .venv 与 python_embed"""
        items_to_keep = {".venv", "python_embed", "setup_env.bat", "Create_Desktop_Shortcut.bat"}
        for entry in os.listdir(self.target_dir):
            if entry in items_to_keep:
                continue
            entry_path = os.path.join(self.target_dir, entry)
            try:
                if os.path.isdir(entry_path):
                    shutil.rmtree(entry_path, ignore_errors=True)
                else:
                    os.remove(entry_path)
            except Exception:
                pass

    def schedule_full_dir_deletion(self):
        """生成临时清理批处理，等待主进程退出后彻底删除整个目录"""
        temp_dir = os.environ.get("TEMP", os.environ.get("TMP", "C:\\"))
        cleaner_bat = os.path.join(temp_dir, "labelimg2_uninstall_cleaner.bat")
        
        script_content = f"""@echo off
timeout /t 2 /nobreak >nul
if exist "{self.target_dir}" (
    rmdir /s /q "{self.target_dir}"
)
del "%~f0"
"""
        with open(cleaner_bat, "w", encoding="utf-8") as f:
            f.write(script_content)

        subprocess.Popen(["cmd.exe", "/c", cleaner_bat], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)


def cli_fallback_uninstall(target_dir: str):
    """当无 PyQt 环境时的纯命令行降级交互"""
    print("==================================================================")
    print("                    LabelImg2 软件卸载向导")
    print("==================================================================")
    print(f"安装路径: {target_dir}")
    print("\n请选择卸载模式:")
    print("1. 彻底删除（已确定以后不再使用 - 删除全部文件与环境）")
    print("2. 保留配置的环境（后期可能继续使用 - 仅删除源码保留 Python 环境）")
    print("3. 取消退出")
    
    choice = input("\n请输入数字 [1/2/3] 并按回车: ").strip()
    if choice == '1':
        print("[*] 正在彻底删除...")
        ps_cmd = "$d = [Environment]::GetFolderPath('Desktop'); $lnk = $d + '\\LabelImg2.lnk'; if (Test-Path $lnk) { Remove-Item -Force $lnk }"
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
        
        temp_dir = os.environ.get("TEMP", "C:\\")
        cleaner_bat = os.path.join(temp_dir, "labelimg2_uninstall_cleaner.bat")
        with open(cleaner_bat, "w", encoding="utf-8") as f:
            f.write(f"@echo off\ntimeout /t 2 /nobreak >nul\nrmdir /s /q \"{target_dir}\"\ndel \"%~f0\"\n")
        subprocess.Popen(["cmd.exe", "/c", cleaner_bat])
        print("[OK] 卸载成功！")
    elif choice == '2':
        print("[*] 正在清理程序文件（保留环境）...")
        items_to_keep = {".venv", "python_embed"}
        for entry in os.listdir(target_dir):
            if entry in items_to_keep:
                continue
            p = os.path.join(target_dir, entry)
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            else:
                try: os.remove(p)
                except Exception: pass
        print("[OK] 程序文件已清理，Python 隔离环境已保留！")
    else:
        print("已取消卸载。")


if __name__ == "__main__":
    target_dir = os.path.abspath(os.path.dirname(__file__))
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        target_dir = os.path.abspath(sys.argv[1])

    if HAS_PYQT:
        app = QApplication(sys.argv)
        dlg = UninstallDialog(target_dir)
        dlg.exec_()
    else:
        cli_fallback_uninstall(target_dir)
