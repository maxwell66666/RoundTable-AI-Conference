#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
重启应用程序脚本
用于停止当前运行的应用程序并启动新实例
"""

import os
import sys
import time
import signal
import subprocess
import psutil

def find_process_by_name(name):
    """查找指定名称的进程"""
    result = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if name in proc.info['name'] or \
               any(name in cmd for cmd in proc.info['cmdline'] if cmd):
                result.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return result

def main():
    """主函数"""
    print("正在重启应用程序...")
    
    # 查找并终止当前运行的应用程序实例
    app_processes = find_process_by_name("app.py")
    if app_processes:
        print(f"找到 {len(app_processes)} 个运行中的应用程序实例")
        for proc in app_processes:
            try:
                pid = proc.pid
                print(f"正在终止进程 {pid}...")
                if sys.platform == "win32":
                    os.kill(pid, signal.SIGTERM)
                else:
                    os.kill(pid, signal.SIGTERM)
                print(f"进程 {pid} 已终止")
            except Exception as e:
                print(f"终止进程 {pid} 时出错: {str(e)}")
        
        # 等待进程完全终止
        print("等待进程完全终止...")
        time.sleep(2)
    else:
        print("未找到运行中的应用程序实例")
    
    # 启动新的应用程序实例
    print("正在启动新的应用程序实例...")
    try:
        # 使用UTF-8编码启动进程，避免中文字符问题
        subprocess.Popen(
            [sys.executable, "app.py"],
            env=dict(os.environ, PYTHONIOENCODING='utf-8'),
            encoding='utf-8'
        )
        print("应用程序已成功启动")
    except Exception as e:
        print(f"启动应用程序时出错: {str(e)}")
    
    print("重启完成")

if __name__ == "__main__":
    main() 