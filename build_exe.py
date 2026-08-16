# -*- coding: utf-8 -*-
"""
LabelImg2 - PyInstaller 打包构建脚本
将 LabelImg2 打包为可独立分发的 Windows 桌面应用程序 (.exe)
"""

import os
import sys
import subprocess
import shutil

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

def check_pyinstaller():
    try:
        import PyInstaller
        print(f"[OK] PyInstaller 已安装, 版本: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("[*] 正在安装 PyInstaller...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "pyinstaller",
            "-i", "http://mirrors.aliyun.com/pypi/simple/",
            "--trusted-host", "mirrors.aliyun.com"
        ])
        return True

def build():
    check_pyinstaller()

    icon_path = os.path.join(ROOT_DIR, "img", "labelImg2.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(ROOT_DIR, "img", "labelImg2.png")

    data_args = [
        f"--add-data={os.path.join(ROOT_DIR, 'img')};img",
        f"--add-data={os.path.join(ROOT_DIR, 'data')};data",
    ]

    for model_f in ["yolov8n.pt", "yolo26n.pt"]:
        model_path = os.path.join(ROOT_DIR, model_f)
        if os.path.exists(model_path):
            data_args.append(f"--add-data={model_path};.")

    collect_args = [
        "--collect-all=ultralytics",
        "--collect-all=yamlloader",
    ]

    hidden_imports = [
        "--hidden-import=PyQt5",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=ultralytics",
        "--hidden-import=torch",
        "--hidden-import=torchvision",
        "--hidden-import=cv2",
        "--hidden-import=PIL",
        "--hidden-import=lxml",
        "--hidden-import=yaml",
        "--hidden-import=yamlloader",
        "--hidden-import=core",
        "--hidden-import=ui",
        "--hidden-import=utils",
        "--hidden-import=libs",
    ]

    exclude_args = [
        "--exclude-module=PyQt6",
        "--exclude-module=PySide2",
        "--exclude-module=PySide6",
        "--exclude-module=tkinter",
        "--exclude-module=matplotlib",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",             # 目录分发模式 (启动速度快，适合包含 PyTorch 的大型应用)
        "--windowed",           # 无黑框控制台
        f"--name=LabelImg2",
        f"--icon={icon_path}",
        *data_args,
        *collect_args,
        *hidden_imports,
        *exclude_args,
        os.path.join(ROOT_DIR, "labelImg.py")
    ]


    print("\n=======================================================")
    print("正在执行 PyInstaller 打包构建命令:")
    print(" ".join(cmd))
    print("=======================================================\n")

    result = subprocess.run(cmd, cwd=ROOT_DIR)
    if result.returncode == 0:
        dist_dir = os.path.join(ROOT_DIR, "dist", "LabelImg2")
        zip_output = os.path.join(ROOT_DIR, "dist", "LabelImg2-v2.0-Windows-x64.zip")
        print("\n=======================================================")
        print(f"[成功] LabelImg2 独立应用已成功构建！")
        print(f"输出目录: {dist_dir}")
        print(f"主执行程序: {os.path.join(dist_dir, 'LabelImg2.exe')}")
        print("正在自动生成发布压缩包 (ZIP)...")
        try:
            shutil.make_archive(os.path.splitext(zip_output)[0], 'zip', dist_dir)
            print(f"[成功] 发布压缩包已生成: {zip_output}")
        except Exception as e:
            print(f"[提示] ZIP 压缩跳过: {e}")
        print("=======================================================\n")
    else:
        print(f"\n[错误] 构建失败，退出码: {result.returncode}")


if __name__ == "__main__":
    build()
