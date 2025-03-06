import sqlite3
import json
from datetime import datetime
from agent_db import get_agent, list_agents, get_random_agents

# 定义 Conference 类
class Conference:
    def __init__(self, conference_id, title, agenda, participant_agent_ids, current_phase_index=-1):
        self.conference_id = conference_id
        self.title = title
        self.agenda = agenda  # 包含摘要的阶段字典列表
        self.participant_agent_ids = participant_agent_ids  # 代理ID列表
        self.start_time = None
        self.end_time = None
        self.summary = None
        self.current_phase_index = current_phase_index  # 现在保存到数据库

def with_db_connection(func):
    """数据库连接装饰器，自动管理连接和事务"""
    def wrapper(*args, **kwargs):
        conn = sqlite3.connect('conferences.db')
        try:
            conn.row_factory = sqlite3.Row  # 启用行工厂
            result = func(conn=conn, *args, **kwargs)
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    return wrapper

# 保存会议到数据库的辅助函数
@with_db_connection
def _save_conference(conference, conn=None):
    """保存会议更新到数据库
    
    参数:
        conference: 会议对象
        conn: 数据库连接, 由装饰器提供, 不应直接传递
    """
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE conferences SET
            title = ?,
            agenda = ?,
            participant_agent_ids = ?,
            start_time = ?,
            end_time = ?,
            summary = ?,
            current_phase_index = ?
        WHERE conference_id = ?
    ''', (
        conference.title,
        json.dumps(conference.agenda),
        json.dumps(conference.participant_agent_ids),
        conference.start_time,
        conference.end_time,
        conference.summary,
        conference.current_phase_index,
        conference.conference_id
    ))

# 创建会议的函数
@with_db_connection
def init_conference_db(conn):
    """初始化会议数据库表结构"""
    cursor = conn.cursor()
    
    # 创建会议表（带NOT NULL约束）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conferences (
            conference_id TEXT PRIMARY KEY NOT NULL,
            title TEXT NOT NULL,
            agenda TEXT NOT NULL,
            participant_agent_ids TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            summary TEXT,
            current_phase_index INTEGER DEFAULT -1 NOT NULL
        )
    ''')

@with_db_connection
def create_conference(conference_id, title, agenda, participant_agent_ids, conn):
    cursor = conn.cursor()
    
    # 检查会议是否已存在
    cursor.execute('SELECT conference_id FROM conferences WHERE conference_id = ?', (conference_id,))
    if cursor.fetchone():
        raise ValueError(f"会议ID {conference_id} 已存在")

    # 验证代理ID
    for agent_id in participant_agent_ids:
        if not get_agent(agent_id):
            raise ValueError(f"代理ID {agent_id} 不存在")

    # 创建并保存会议对象
    conference = Conference(conference_id, title, agenda, participant_agent_ids)
    cursor.execute('''
        INSERT INTO conferences 
        (conference_id, title, agenda, participant_agent_ids, current_phase_index)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        conference.conference_id,
        conference.title,
        json.dumps(conference.agenda),
        json.dumps(conference.participant_agent_ids),
        conference.current_phase_index
    ))

    print(f"会议 '{conference.title}' 创建成功！")
    return conference

def start_conference(conference_id):
    conference = get_conference(conference_id)  # Assume this retrieves a conference object
    if not conference:
        print(f"No conference found with ID {conference_id}!")
        return False
    if conference.start_time:
        print(f"Conference '{conference.title}' has already started!")
        return False
    conference.start_time = datetime.now().isoformat()
    conference.current_phase_index = 0
    
    # 直接调用_save_conference，不传递conn参数
    _save_conference(conference)
    
    print(f"Conference '{conference.title}' has started!")
    return True

@with_db_connection
def get_conference(conference_id, conn):
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM conferences WHERE conference_id = ?', (conference_id,))
    row = cursor.fetchone()

    if row:
        current_phase_index = row[7] if len(row) > 7 else -1
        conference = Conference(
            row[0],  # conference_id
            row[1],  # title
            json.loads(row[2]),  # agenda
            json.loads(row[3]),  # participant_agent_ids
            current_phase_index  # current_phase_index (默认 -1 如果缺失)
        )
        conference.start_time = row[4]
        conference.end_time = row[5]
        conference.summary = row[6]
        return conference
    return None

@with_db_connection
def list_conferences(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM conferences')
    return [
        Conference(
            row['conference_id'],
            row['title'],
            json.loads(row['agenda']),
            json.loads(row['participant_agent_ids']),
            row['current_phase_index']
        ) for row in cursor.fetchall()
    ]

def advance_phase(conference_id):
    conference = get_conference(conference_id)
    if not conference:
        raise ValueError("会议不存在")
    if conference.current_phase_index >= len(conference.agenda) - 1:
        raise ValueError("已经是最后一个阶段")
    conference.current_phase_index += 1
    
    # 直接调用_save_conference，不传递conn参数
    _save_conference(conference)
    
    return conference

def end_phase(conference_id):
    conference = get_conference(conference_id)
    if not conference:
        raise ValueError("会议不存在")
    # 可以在这里添加阶段总结等逻辑
    
    # 直接调用_save_conference，不传递conn参数
    _save_conference(conference)
    
    return conference

def end_conference(conference_id):
    conference = get_conference(conference_id)
    if not conference:
        raise ValueError("会议不存在")
    conference.end_time = datetime.now().isoformat()
    # 可以在这里生成会议总结
    
    # 直接调用_save_conference，不传递conn参数
    _save_conference(conference)
    
    return conference

@with_db_connection
def delete_conference(conference_id, conn=None):
    """
    从数据库中删除指定ID的会议
    
    参数:
        conference_id: 要删除的会议ID
        conn: 数据库连接(由装饰器提供)
    
    返回:
        布尔值，表示是否成功删除
    """
    cursor = conn.cursor()
    
    # 检查会议是否存在
    cursor.execute('SELECT conference_id FROM conferences WHERE conference_id = ?', (conference_id,))
    if not cursor.fetchone():
        raise ValueError(f"会议ID {conference_id} 不存在")
    
    # 执行删除操作
    cursor.execute('DELETE FROM conferences WHERE conference_id = ?', (conference_id,))
    
    # 检查删除是否成功
    if cursor.rowcount > 0:
        print(f"会议 {conference_id} 已成功删除")
        return True
    else:
        print(f"删除会议 {conference_id} 失败")
        return False
