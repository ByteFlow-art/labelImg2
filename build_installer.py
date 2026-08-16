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

def build_helper_executables():
    icon_path = os.path.join(ROOT_DIR, "img", "labelImg2.ico")
    version_info_path = os.path.join(ROOT_DIR, "version_info.txt")
    version_arg = [f"--version-file={version_info_path}"] if os.path.exists(version_info_path) else []

    # 1. 构建主程序启动器 LabelImg2.exe
    print("[*] 正在构建主程序专属启动器: LabelImg2.exe ...")
    cmd_launcher = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--onefile", "--windowed",
        "--name=LabelImg2",
        f"--icon={icon_path}",
        *version_arg,
        "--distpath", ROOT_DIR,
        os.path.join(ROOT_DIR, "launcher.py")
    ]
    subprocess.run(cmd_launcher, cwd=ROOT_DIR)

    # 2. 构建一键卸载清理器 Uninstall.exe
    print("[*] 正在构建一键卸载清理器: Uninstall.exe ...")
    cmd_uninstall = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--onefile", "--windowed",
        "--name=Uninstall",
        f"--icon={icon_path}",
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
        "--distpath", ROOT_DIR,
        os.path.join(ROOT_DIR, "uninstaller_gui.py")
    ]
    subprocess.run(cmd_uninstall, cwd=ROOT_DIR)

def create_payload_zip():
    payload_path = os.path.join(ROOT_DIR, "app_payload.zip")
    print(f"[*] 正在打包核心程序载荷: {payload_path} ...")

    include_dirs = ["core", "libs", "ui", "utils", "data", "img"]
    include_files = [
        "labelImg.py", "main.py", "requirements.txt",
        "LabelImg2.exe", "Uninstall.exe",
        "Start_LabelImg2.bat", "Launch_LabelImg2.bat", "setup_env.bat", "Create_Desktop_Shortcut.bat",
        "一键安装LabelImg2.bat", "一键彻底卸载LabelImg2.bat",
        "yolov8n.pt", "yolo26n.pt", "LICENSE", "README.md"
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
    build_helper_executables()
    payload_zip = create_payload_zip()

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
        unblock_bat = os.path.join(ROOT_DIR, "一键安装LabelImg2.bat")
        print("\n=======================================================")
        print(f"[成功] LabelImg2 独立安装程序已成功生成！")
        print(f"安装包路径: {exe_path}")
        print(f"安装包大小: {os.path.getsize(exe_path) / (1024*1024):.2f} MB")
        
        print("正在自动生成防浏览器拦截与防SmartScreen拦截的发布压缩包 (ZIP)...")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(exe_path, f"{out_name}.exe")
            if os.path.exists(unblock_bat):
                zf.write(unblock_bat, "一键安装LabelImg2.bat")
        print(f"[成功] 防拦截安装压缩包已生成: {zip_path}")
        print(f"压缩包大小: {os.path.getsize(zip_path) / (1024*1024):.2f} MB")
        print("=======================================================\n")
    else:
        print(f"\n[错误] 安装程序构建失败，退出码: {result.returncode}")

    if os.path.exists(payload_zip):
        os.remove(payload_zip)

if __name__ == "__main__":
    build_installer()

