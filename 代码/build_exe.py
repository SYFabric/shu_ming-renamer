# -*- coding: utf-8 -*-
"""
打包脚本：将 rename_by_bracket_ui.py 打包为单个 exe。
用法（在 Windows 命令行，当前目录为脚本所在目录）：
    python build_exe.py

生成的 exe 位于 dist\\Renamer.exe
前提：pip install pyinstaller
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "shuming.py")
ICON = os.path.join(HERE, "icon.ico")

# PyInstaller 命令参数
# --onefile : 打包成单个 exe（启动稍慢于 --onedir，但分发最简单）
# --windowed / --noconsole : 纯 GUI 程序，不弹黑色控制台窗口
# --icon : 设置 exe 文件图标 + 运行时任务栏/窗口图标（需脚本里也调 iconbitmap）
# --name : 输出的 exe 名称
# --clean : 清理缓存，避免旧构建产物干扰
# --exclude-module : 排除不需要的大模块，减小体积、加快启动
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--clean",
    "--name", "Renamer",
    f"--icon={ICON}",
    # 排除常见大体积可选依赖（tkinter 由 PyInstaller 自动处理，不要排除）
    "--exclude-module", "numpy",
    "--exclude-module", "pandas",
    "--exclude-module", "matplotlib",
    "--exclude-module", "PIL",
    "--exclude-module", "PIL.Image",
    "--exclude-module", "scipy",
    "--exclude-module", "sklearn",
    "--exclude-module", "torch",
    "--exclude-module", "tensorflow",
    SCRIPT,
]

print(">>> 执行命令：")
print(" ".join(cmd))
print("-" * 60)

ret = subprocess.run(cmd)
sys.exit(ret.returncode)
