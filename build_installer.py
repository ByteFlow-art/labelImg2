# -*- coding: utf-8 -*-
"""
LabelImg2 - 官方独立安装程序打包脚本 (Build Standalone Installer EXE)
生成单个轻量级、带专属 App 图标的安装包：LabelImg2_Setup_v1.0.0.exe
"""

import os
import sys
import shutil
import zipfile
import subprocess

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

def create_payload_zip():
    payload_path = os.path.join(ROOT_DIR, "app_payload.zip")
    print(f"[*] 正在打包核心程序载荷: {payload_path} ...")

    include_dirs = ["core", "libs", "ui", "utils", "data", "img"]
    include_files = [
        "labelImg.py", "main.py", "requirements.txt",
        "Start_LabelImg2.bat", "setup_env.bat", "Create_Desktop_Shortcut.bat",
        "uninstall_gui.py", "Uninstall_LabelImg2.bat",
        "yolov8n.pt", "yolo26n.pt", "LICENSE", "README.md", "界面预览.png"
    ]

    with zipfile.ZipFile(payload_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for d in include_dirs:
            dp = os.path.join(ROOT_DIR, d)
            if os.path.exists(dp):
                for root, _, files in os.walk(dp):
                    if any(x in root for x in ["__pycache__", ".git", ".venv", "dist", "build"]):
                        continue
                    for f in files:
                        fp = os.path.join(root, f)
                        rel = os.path.relpath(fp, ROOT_DIR)
                        zf.write(fp, rel)

        for f in include_files:
            fp = os.path.join(ROOT_DIR, f)
            if os.path.exists(fp):
                zf.write(fp, f)

    print(f"[OK] 核心程序载荷打包完成，大小: {os.path.getsize(payload_path) / (1024*1024):.2f} MB")
    return payload_path

def build_installer():
    payload_zip = create_payload_zip()

    icon_path = os.path.join(ROOT_DIR, "img", "app.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(ROOT_DIR, "img", "labelImg2.ico")

    version_info_path = os.path.join(ROOT_DIR, "version_info.txt")
    version_arg = [f"--version-file={version_info_path}"] if os.path.exists(version_info_path) else []

    out_name = "LabelImg2_Setup_v1.0.0"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f"--name={out_name}",
        f"--icon={icon_path}",
        f"--add-data={payload_zip};.",
        f"--add-data={os.path.join(ROOT_DIR, 'img')};img",
        *version_arg,
        "--collect-all", "PyQt5",
        "--exclude-module=torch",
        "--exclude-module=torchvision",
        "--exclude-module=ultralytics",
        "--exclude-module=matplotlib",
        "--exclude-module=tkinter",
        "--exclude-module=PyQt6",
        "--exclude-module=PySide2",
        "--exclude-module=PySide6",
        os.path.join(ROOT_DIR, "installer_gui.py")
    ]

    print("\n=======================================================")
    print("正在构建 LabelImg2 独立安装程序 EXE:")
    print(" ".join(cmd))
    print("=======================================================\n")

    result = subprocess.run(cmd, cwd=ROOT_DIR)

    if result.returncode == 0:
        exe_path = os.path.join(ROOT_DIR, "dist", f"{out_name}.exe")
        print("\n=======================================================")
        print(f"[成功] LabelImg2 独立安装程序已成功生成！")
        print(f"安装包路径: {exe_path}")
        print(f"安装包大小: {os.path.getsize(exe_path) / (1024*1024):.2f} MB")
        print("=======================================================\n")
    else:
        print(f"\n[错误] 安装程序构建失败，退出码: {result.returncode}")

    if os.path.exists(payload_zip):
        try:
            os.remove(payload_zip)
        except Exception:
            pass

    # 清理 PyInstaller 产生的 build 临时中间文件夹与 spec 文件
    build_dir = os.path.join(ROOT_DIR, "build")
    if os.path.exists(build_dir):
        try:
            shutil.rmtree(build_dir, ignore_errors=True)
        except Exception:
            pass

    spec_file = os.path.join(ROOT_DIR, f"{out_name}.spec")
    if os.path.exists(spec_file):
        try:
            os.remove(spec_file)
        except Exception:
            pass

if __name__ == "__main__":
    build_installer()
