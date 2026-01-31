#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GUI游戏启动脚本 - 自动修复 Tcl/Tk 路径问题
"""

import os
import sys
import subprocess
import glob

def find_python_tcl_path():
    """查找 Python 安装目录中的 tcl/tk 路径"""
    # 获取基础 Python 路径（非虚拟环境）
    python_base = sys.base_prefix
    
    # Windows 上常见的路径
    search_paths = [
        os.path.join(python_base, 'tcl'),
        os.path.join(python_base, 'lib'),
        os.path.join(python_base, 'Library', 'lib'),
        # 常见的 Python 安装位置
        r'C:\Users\lcx\AppData\Local\Programs\Python\Python313\tcl',
        r'C:\Users\lcx\AppData\Local\Programs\Python\Python312\tcl',
        r'C:\Users\lcx\AppData\Local\Programs\Python\Python311\tcl',
        r'C:\Python313\tcl',
        r'C:\Python312\tcl',
        r'C:\Python311\tcl',
    ]
    
    tcl_path = None
    tk_path = None
    
    for base_path in search_paths:
        # 查找 tcl8.6 目录
        tcl_candidates = glob.glob(os.path.join(base_path, 'tcl8*'))
        tk_candidates = glob.glob(os.path.join(base_path, 'tk8*'))
        
        if tcl_candidates:
            tcl_path = tcl_candidates[0]
        if tk_candidates:
            tk_path = tk_candidates[0]
        
        if tcl_path and tk_path:
            break
    
    return tcl_path, tk_path

def main():
    print("=" * 50)
    print("《仙途问道》GUI启动器")
    print("=" * 50)
    print()
    
    # 查找 Tcl/Tk 路径
    print("正在查找 Tcl/Tk 库...")
    tcl_path, tk_path = find_python_tcl_path()
    
    if tcl_path and os.path.exists(tcl_path):
        os.environ['TCL_LIBRARY'] = tcl_path
        print(f"  TCL_LIBRARY = {tcl_path}")
    else:
        print("  警告：未找到 TCL_LIBRARY")
    
    if tk_path and os.path.exists(tk_path):
        os.environ['TK_LIBRARY'] = tk_path
        print(f"  TK_LIBRARY = {tk_path}")
    else:
        print("  警告：未找到 TK_LIBRARY")
    
    print()
    
    # 尝试导入 tkinter 测试
    print("正在测试 tkinter...")
    try:
        import tkinter
        print("  tkinter 导入成功！")
        print()
    except Exception as e:
        print(f"  tkinter 导入失败：{e}")
        print()
        print("解决方案：")
        print("1. 重新安装 Python，确保勾选 'tcl/tk and IDLE' 选项")
        print("2. 或者在虚拟环境外运行游戏")
        print("3. 或者手动设置环境变量：")
        print("   set TCL_LIBRARY=<Python安装目录>/tcl/tcl8.6")
        print("   set TK_LIBRARY=<Python安装目录>/tcl/tk8.6")
        return
    
    # 启动游戏
    print("正在启动游戏...")
    print()
    
    # 获取命令行参数
    args = sys.argv[1:]
    
    # 导入并运行游戏
    try:
        from gui_game import main as gui_main
        gui_main()
    except Exception as e:
        print(f"启动失败：{e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")

if __name__ == "__main__":
    main()
