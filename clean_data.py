#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
清理数据脚本
用于清理个人数据，准备上传到 GitHub
"""

import os
import sqlite3
import shutil
import glob

def clean_database(db_path, keep_structure=True):
    """清理数据库，保留结构但删除所有数据"""
    if not os.path.exists(db_path):
        print(f"数据库 {db_path} 不存在，跳过")
        return
    
    if keep_structure:
        # 保留结构但删除所有数据
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        # 删除每个表中的所有数据
        for table in tables:
            table_name = table[0]
            if table_name != "sqlite_sequence":  # 跳过 sqlite 内部表
                cursor.execute(f"DELETE FROM {table_name};")
        
        conn.commit()
        conn.close()
        print(f"已清空数据库 {db_path} 中的所有数据")
    else:
        # 直接删除数据库文件
        os.remove(db_path)
        print(f"已删除数据库 {db_path}")

def clean_dialogue_histories():
    """清理对话历史目录"""
    history_dir = "dialogue_histories"
    if os.path.exists(history_dir):
        # 删除目录中的所有文件
        for file in glob.glob(os.path.join(history_dir, "*")):
            os.remove(file)
        print(f"已清空 {history_dir} 目录")
    else:
        # 创建目录
        os.makedirs(history_dir)
        print(f"已创建 {history_dir} 目录")

def remove_env_file():
    """删除 .env 文件"""
    if os.path.exists(".env"):
        os.remove(".env")
        print("已删除 .env 文件")
    else:
        print(".env 文件不存在，跳过")

def main():
    """主函数"""
    print("开始清理数据...")
    
    # 清理数据库
    clean_database("agents.db", keep_structure=True)
    clean_database("conferences.db", keep_structure=True)
    clean_database("conversations.db", keep_structure=True)
    
    # 清理对话历史
    clean_dialogue_histories()
    
    # 删除 .env 文件
    remove_env_file()
    
    print("数据清理完成！")
    print("请确保 .env.example 文件中不包含任何个人 API 密钥")
    print("现在可以安全地将代码上传到 GitHub")

if __name__ == "__main__":
    main() 