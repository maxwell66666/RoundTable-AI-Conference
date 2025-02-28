"""
数据库迁移模块
管理数据库架构的变更和版本控制
"""

import os
import sqlite3
import json
from datetime import datetime
from version import get_db_schema_version

# 迁移历史表名
MIGRATION_TABLE = "db_migrations"

def init_migration_table(conn):
    """初始化迁移历史表"""
    cursor = conn.cursor()
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL,
            applied_at TIMESTAMP NOT NULL,
            description TEXT
        )
    ''')
    conn.commit()

def get_current_db_version(conn):
    """获取数据库当前版本"""
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT version FROM {MIGRATION_TABLE} ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        return result[0] if result else "0.0"
    except sqlite3.OperationalError:
        # 表不存在，返回初始版本
        return "0.0"

def record_migration(conn, version, description):
    """记录迁移历史"""
    cursor = conn.cursor()
    cursor.execute(
        f"INSERT INTO {MIGRATION_TABLE} (version, applied_at, description) VALUES (?, ?, ?)",
        (version, datetime.now().isoformat(), description)
    )
    conn.commit()

def get_all_migrations(conn):
    """获取所有迁移历史"""
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT id, version, applied_at, description FROM {MIGRATION_TABLE} ORDER BY id")
        return cursor.fetchall()
    except sqlite3.OperationalError:
        return []

# 迁移脚本字典
# 键是版本号，值是包含SQL语句和描述的元组
MIGRATIONS = {
    "1.0": (
        """
        -- 初始化agents表
        CREATE TABLE IF NOT EXISTS agents (
            agent_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            data JSON NOT NULL
        );
        
        -- 初始化conferences表
        CREATE TABLE IF NOT EXISTS conferences (
            conference_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            current_phase_index INTEGER NOT NULL,
            data JSON NOT NULL
        );
        
        -- 初始化conversations表
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conference_id TEXT,
            phase_id INTEGER,
            agent_id TEXT,
            speech TEXT,
            timestamp TEXT
        );
        
        -- 创建索引加速查询
        CREATE INDEX IF NOT EXISTS idx_conversations_conference_phase
        ON conversations(conference_id, phase_id);
        """,
        "初始数据库架构"
    ),
    
    "1.1": (
        """
        -- 添加回答评分表
        CREATE TABLE IF NOT EXISTS response_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conference_id TEXT,
            phase_id INTEGER,
            agent_id TEXT,
            speech_id INTEGER,
            rating INTEGER,
            feedback TEXT,
            timestamp TEXT,
            FOREIGN KEY(speech_id) REFERENCES conversations(id)
        );
        
        -- 添加用户表
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL,
            last_login TEXT
        );
        """,
        "添加回答评分和用户表"
    )
}

def run_migrations(db_path="conversations.db"):
    """运行所有待执行的迁移"""
    conn = sqlite3.connect(db_path)
    
    # 确保迁移表存在
    init_migration_table(conn)
    
    # 获取当前数据库版本
    current_version = get_current_db_version(conn)
    print(f"当前数据库版本: {current_version}")
    
    # 目标版本
    target_version = get_db_schema_version()
    print(f"目标数据库版本: {target_version}")
    
    # 如果当前版本已经是最新
    if current_version == target_version:
        print("数据库已是最新版本，无需迁移")
        conn.close()
        return
    
    # 获取所有需要执行的迁移
    versions_to_apply = []
    for version in sorted(MIGRATIONS.keys()):
        if version > current_version and version <= target_version:
            versions_to_apply.append(version)
    
    if not versions_to_apply:
        print("没有需要执行的迁移")
        conn.close()
        return
    
    # 执行迁移
    for version in versions_to_apply:
        sql, description = MIGRATIONS[version]
        print(f"正在应用迁移 {version}: {description}")
        try:
            cursor = conn.cursor()
            cursor.executescript(sql)
            conn.commit()
            record_migration(conn, version, description)
            print(f"迁移 {version} 应用成功")
        except Exception as e:
            conn.rollback()
            print(f"迁移 {version} 失败: {str(e)}")
            raise
    
    print(f"所有迁移完成，当前数据库版本: {target_version}")
    conn.close()

def show_migration_history(db_path="conversations.db"):
    """显示迁移历史"""
    conn = sqlite3.connect(db_path)
    migrations = get_all_migrations(conn)
    
    if not migrations:
        print("没有迁移历史记录")
    else:
        print("迁移历史:")
        for migration in migrations:
            print(f"ID: {migration[0]}, 版本: {migration[1]}, 时间: {migration[2]}, 描述: {migration[3]}")
    
    conn.close()

if __name__ == "__main__":
    # 当作为脚本执行时，运行迁移
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "history":
        show_migration_history()
    else:
        run_migrations() 