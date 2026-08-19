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
        zip_path = os.path.join(ROOT_DIR, "dist", f"{out_name}.zip")
        print("\n=======================================================")
        print(f"[成功] LabelImg2 独立安装程序已成功生成！")
        print(f"安装包路径: {exe_path}")
        print(f"安装包大小: {os.path.getsize(exe_path) / (1024*1024):.2f} MB")
        
        print("正在自动生成发布压缩包 (ZIP)...")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(exe_path, f"{out_name}.exe")
        print(f"[成功] 发布压缩包已生成: {zip_path}")
        print(f"压缩包大小: {os.path.getsize(zip_path) / (1024*1024):.2f} MB")
        print("=======================================================\n")
    else:
        print(f"\n[错误] 安装程序构建失败，退出码: {result.returncode}")

    if os.path.exists(payload_zip):
        os.remove(payload_zip)

if __name__ == "__main__":
    build_installer()
