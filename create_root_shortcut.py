# -*- coding: utf-8 -*-
import os
import subprocess

root_dir = os.path.abspath(os.path.dirname(__file__))
target_bat = os.path.join(root_dir, 'Start_LabelImg2.bat')
icon_path = os.path.join(root_dir, 'img', 'labelImg2.ico')

for name in ['启动LabelImg2.lnk', 'LabelImg2.lnk']:
    lnk_path = os.path.join(root_dir, name)
    ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{lnk_path}')
$Shortcut.TargetPath = '{target_bat}'
$Shortcut.WorkingDirectory = '{root_dir}'
$Shortcut.IconLocation = '{icon_path},0'
$Shortcut.Description = 'LabelImg2 Next-Gen - AI 智能计算机视觉标注工作台'
$Shortcut.Save()
"""
    subprocess.run(['powershell', '-NoProfile', '-Command', ps_script], check=True)
    print(f"[OK] 成功创建快捷方式: {lnk_path}")

if __name__ == '__main__':
    print("快捷方式生成完成！")
