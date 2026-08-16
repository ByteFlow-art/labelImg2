# -*- coding: utf-8 -*-
"""
LabelImg2 - 官方桌面启动器 (Windows Standalone Launcher)
内置专属 App 图标，自动寻径 Python 环境并静默启动 LabelImg2，无黑框。
"""

import os
import sys
import subprocess

def main():
    root_dir = os.path.abspath(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__))
    
    # 1. 优先级探测 Python 环境
    python_candidates = [
        os.path.join(root_dir, ".venv", "Scripts", "pythonw.exe"),
        os.path.join(root_dir, ".venv", "Scripts", "python.exe"),
        os.path.join(root_dir, "python_embed", "pythonw.exe"),
        os.path.join(root_dir, "python_embed", "python.exe"),
    ]
    
    python_exe = None
    for p in python_candidates:
        if os.path.exists(p):
            python_exe = p
            break
            
    # 2. 如果未找到本地环境，尝试全局 python / conda
    if not python_exe:
        for p in ["pythonw.exe", "python.exe"]:
            p_path = shutil.which(p) if 'shutil' in sys.modules else None
            if p_path:
                python_exe = p_path
                break
                
    main_py = os.path.join(root_dir, "labelImg.py")
    
    if python_exe and os.path.exists(main_py):
        # 启动主程序
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        subprocess.Popen([python_exe, main_py] + sys.argv[1:], cwd=root_dir, creationflags=flags)
    else:
        # 如果未初始化环境，调用 Start_LabelImg2.bat 进行初始化并启动
        bat_launcher = os.path.join(root_dir, "Start_LabelImg2.bat")
        if os.path.exists(bat_launcher):
            subprocess.Popen(["cmd.exe", "/c", bat_launcher], cwd=root_dir)
        else:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "未找到 LabelImg2 运行环境与主程序，请先运行 setup_env.bat 进行初始化。", "LabelImg2 启动提示", 0x10)

if __name__ == "__main__":
    main()
