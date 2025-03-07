from fastapi import FastAPI, Request, Form, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

import sqlite3
import json
import logging
from round_table import start_phase_discussion, user_intervene, get_agent_name_by_id
from conference_organizer import (
    create_conference, start_conference, advance_phase, 
    end_phase, end_conference, get_conference, 
    list_conferences, init_conference_db, delete_conference
)
from agent_db import list_agents, init_agent_db
from datetime import datetime, timedelta
import asyncio
import concurrent.futures
from typing import List, Dict, Any
from starlette.websockets import WebSocketState
import threading
from version import get_version, get_version_info
from db_migrations import run_migrations
import os
import random
import uuid
import shutil

# 初始化日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("roundtable")

app = FastAPI(title="RoundTable对话系统", version=get_version())

# 挂载静态文件目录（用于CSS等静态资源）
app.mount("/static", StaticFiles(directory="static"), name="static")

# 设置Jinja2模板
templates = Jinja2Templates(directory="templates")

# 版本信息
VERSION_INFO = get_version_info()

def generate_agenda(topic):
    """根据主题生成会议议程"""
    agenda = [
        {
            "phase_name": "主题讨论",
            "topics": [topic],
            "description": f"对 '{topic}' 进行深入讨论，分享各自观点和见解"
        },
        {
            "phase_name": "专家分享",
            "topics": [topic],
            "description": f"各位专家轮流分享关于 '{topic}' 的专业知识和经验"
        },
        {
            "phase_name": "问答",
            "topics": [topic],
            "description": f"针对 '{topic}' 提出疑问并回答其他参与者的问题"
        },
        {
            "phase_name": "总结",
            "topics": [topic],
            "description": f"归纳讨论中的关键点，提出具体可行的结论和建议"
        }
    ]
    return agenda

# 管理WebSocket连接
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, conference_id: str):
        await websocket.accept()
        if conference_id not in self.active_connections:
            self.active_connections[conference_id] = []
        self.active_connections[conference_id].append(websocket)

    def disconnect(self, websocket: WebSocket, conference_id: str):
        if conference_id in self.active_connections:
            if websocket in self.active_connections[conference_id]:
                self.active_connections[conference_id].remove(websocket)
            if not self.active_connections[conference_id]:
                del self.active_connections[conference_id]

    async def send_dialogue(self, message: Dict[str, Any], conference_id: str):
        if conference_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[conference_id]:
                try:
                    if connection.client_state == WebSocketState.CONNECTED:
                        await connection.send_json(message)
                except Exception:
                    dead_connections.append(connection)
            
            # 清理断开的连接
            for dead in dead_connections:
                self.disconnect(dead, conference_id)

manager = ConnectionManager()

# 设置对话流监听器
dialogue_listeners = {}

# 初始化对话历史数据库
def init_conversation_db():
    conn = sqlite3.connect('conversations.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conference_id TEXT,
            phase_id INTEGER,
            agent_id TEXT,
            speech TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

def create_app():
    app = FastAPI(title="RoundTable对话系统", version=get_version())
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # 初始化数据库
    @app.on_event("startup")
    async def startup_db_client():
        print(f"正在启动 {VERSION_INFO['name']} v{VERSION_INFO['version']} (构建 {VERSION_INFO['build']})")
        print("正在运行数据库迁移...")
        run_migrations()
        print("正在初始化数据库...")
        init_conversation_db()
        init_conference_db()
        init_agent_db()
        print("数据库初始化完成")
    
    return app

# 创建应用实例
app = create_app()

# 设置Jinja2模板（需要在app实例之后）
templates = Jinja2Templates(directory="templates")

# 版本API端点
@app.get("/api/version")
async def get_api_version():
    """返回API版本信息"""
    return VERSION_INFO

# 获取所有对话历史文件列表
@app.get("/api/dialogue_histories")
async def get_dialogue_histories():
    # 首先检查旧位置的文件
    old_files = []
    if os.path.exists("."):
        old_files = [f for f in os.listdir(".") if f.startswith("dialogue_history_") and f.endswith(".json")]
    
    # 确保新目录存在
    histories_dir = "dialogue_histories"
    if not os.path.exists(histories_dir):
        os.makedirs(histories_dir)
    
    # 获取新目录中的文件
    new_files = []
    if os.path.exists(histories_dir):
        new_files = [f for f in os.listdir(histories_dir) if f.startswith("dialogue_history_") and f.endswith(".json")]
    
    # 合并文件列表，并移动旧文件到新目录
    files = []
    for filename in old_files:
        # 如果文件不在新目录中，移动它
        if filename not in new_files:
            try:
                shutil.move(filename, os.path.join(histories_dir, filename))
                files.append(filename)
            except Exception as e:
                print(f"移动文件 {filename} 时出错: {str(e)}")
        else:
            files.append(filename)
    
    # 添加新目录中的文件
    for filename in new_files:
        if filename not in files:
            files.append(filename)
    
    histories = []
    
    for filename in files:
        # 确定文件的完整路径
        if os.path.exists(os.path.join(histories_dir, filename)):
            file_path = os.path.join(histories_dir, filename)
        else:
            file_path = filename  # 以防文件仍然在旧位置
        
        if not os.path.exists(file_path):
            continue  # 跳过不存在的文件
            
        file_stats = os.stat(file_path)
        modified_time = datetime.fromtimestamp(file_stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        
        # 从文件名中提取会议ID和阶段ID
        # 文件名格式: dialogue_history_[会议ID]_[阶段ID].json
        parts = filename.replace("dialogue_history_", "").replace(".json", "").split("_")
        if len(parts) >= 2:
            conference_id = parts[0]
            phase_id = parts[1]
            
            # 尝试获取会议标题和会议类型
            conference_title = "未知会议"
            conference_type = "未分类"
            try:
                conference = get_conference(conference_id)
                if conference:
                    conference_title = conference.title
                    conference_type = getattr(conference, 'conference_type', '未分类')
            except Exception as e:
                print(f"获取会议 {conference_id} 时出错: {str(e)}")
            
            histories.append({
                "filename": filename,
                "conference_id": conference_id,
                "phase_id": phase_id,
                "size_kb": round(file_stats.st_size / 1024, 2),
                "modified": modified_time,
                "conference_title": conference_title,
                "conference_type": conference_type
            })
    
    # 按修改时间降序排序
    histories.sort(key=lambda x: x["modified"], reverse=True)
    
    return histories

# 删除对话历史文件
@app.delete("/api/dialogue_histories/{filename}")
async def delete_dialogue_history(filename: str):
    histories_dir = "dialogue_histories"
    
    # 检查文件是否在新位置
    new_path = os.path.join(histories_dir, filename)
    
    # 检查文件是否在旧位置
    old_path = filename
    
    if os.path.exists(new_path):
        try:
            os.remove(new_path)
            return {"message": f"文件 {filename} 已成功删除"}
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": f"删除文件失败: {str(e)}"}
            )
    elif os.path.exists(old_path):
        try:
            os.remove(old_path)
            return {"message": f"文件 {filename} 已成功删除"}
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": f"删除文件失败: {str(e)}"}
            )
    else:
        return JSONResponse(
            status_code=404,
            content={"error": f"文件 {filename} 不存在"}
        )

# WebSocket路由
@app.websocket("/ws/{conference_id}")
async def websocket_endpoint(websocket: WebSocket, conference_id: str):
    await manager.connect(websocket, conference_id)
    try:
        # 发送当前对话历史
        conn = sqlite3.connect('conversations.db')
        cursor = conn.cursor()
        conference = get_conference(conference_id)
        if conference:
            current_phase = conference.current_phase_index
            cursor.execute('SELECT agent_id, speech, timestamp FROM conversations WHERE conference_id = ? AND phase_id = ? ORDER BY id',
                    (conference_id, current_phase))
            for row in cursor.fetchall():
                agent_id = row[0]
                agent_name = get_agent_name_by_id(agent_id) or agent_id
                await websocket.send_json({
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "speech": row[1],
                    "timestamp": row[2]
                })
        conn.close()
        
        # 保持连接打开
        while True:
            # 只是为了保持连接而等待
            data = await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, conference_id)

# 主页
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    conferences = list_conferences()
    # 按开始时间倒序排序，最近的会议排在前面
    # 未开始的会议（start_time为None）排在最后
    conferences = sorted(
        conferences, 
        key=lambda x: datetime.fromisoformat(x.start_time) if x.start_time else datetime.min, 
        reverse=True
    )
    agents = list_agents()
    
    # 为日历准备数据
    today = datetime.now()
    current_month = today.month
    current_year = today.year
    current_day = today.day
    
    # 生成活动统计数据
    # 假设过去30天的活动数据
    activity_data = []
    for i in range(30, 0, -1):
        date = today - timedelta(days=i)
        # 统计每天的会议数量
        day_conferences = [c for c in conferences if c.start_time and 
                          datetime.fromisoformat(c.start_time).date() == date.date()]
        activity_data.append({
            "date": date.strftime("%m-%d"),
            "value": len(day_conferences)
        })
    
    # 为日历准备会议日期
    conference_dates = []
    for conf in conferences:
        if conf.start_time:
            conf_date = datetime.fromisoformat(conf.start_time).date()
            conference_dates.append(conf_date.day)
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "conferences": conferences, 
        "agents": agents,
        "version": VERSION_INFO,
        "current_month": current_month,
        "current_year": current_year,
        "current_day": current_day,
        "activity_data": json.dumps(activity_data),
        "conference_dates": conference_dates,
        "now": today
    })

# 会议管理页面
@app.get("/conferences", response_class=HTMLResponse)
async def conferences_page(request: Request):
    conferences = list_conferences()
    # 按开始时间倒序排序，最近的会议排在前面
    # 未开始的会议（start_time为None）排在最后
    conferences = sorted(
        conferences, 
        key=lambda x: datetime.fromisoformat(x.start_time) if x.start_time else datetime.min, 
        reverse=True
    )
    agents = list_agents()
    return templates.TemplateResponse("conferences.html", {
        "request": request, 
        "conferences": conferences, 
        "agents": agents,
        "version": VERSION_INFO
    })

# 对话历史管理页面
@app.get("/dialogue_histories", response_class=HTMLResponse)
async def dialogue_histories_page(request: Request):
    return templates.TemplateResponse("dialogue_histories.html", {
        "request": request,
        "version": VERSION_INFO
    })

# 专家管理页面
@app.get("/agent", response_class=HTMLResponse)
async def agent_management_page(request: Request):
    agents = list_agents()
    return templates.TemplateResponse("agent_management.html", {
        "request": request,
        "agents": agents,
        "version": VERSION_INFO
    })

# 启动新会议
@app.post("/start_conference", response_class=HTMLResponse)
async def start_new_conference(request: Request):
    form_data = await request.form()
    topic = form_data.get("topic", "")
    conference_title = form_data.get("conference_title", "")
    num_agents_str = form_data.get("num_agents", "5")
    conference_type = form_data.get("conference_type", "战略讨论")  # 获取会议类型
    
    try:
        num_agents = int(num_agents_str)
    except ValueError:
        num_agents = 5  # 默认值
    
    try:
        # 生成动态议程
        agenda = generate_agenda(topic)
        
        # 检查是否有足够的 agent 可用
        available_agents = list_agents()
        if len(available_agents) < num_agents:
            error_html = templates.get_template("error.html").render(
                request=request,
                error_title="专家数量不足",
                error_message=f"需要 {num_agents} 位专家，但只找到 {len(available_agents)} 位。请先添加更多专家。",
                version=VERSION_INFO
            )
            return HTMLResponse(content=error_html)
        
        # 生成 conference ID
        conference_id = f"C{str(uuid.uuid4())[:8]}"
        
        # 如果没有指定标题，使用默认标题
        if not conference_title:
            today = datetime.now().strftime("%Y-%m-%d")
            conference_title = f"{today}会议：{topic[:20]}{'...' if len(topic) > 20 else ''}"
        
        # 创建会议
        conference = create_conference(
            conference_id=conference_id,
            title=conference_title,
            topic=topic,
            num_agents=num_agents,
            conference_type=conference_type  # 添加会议类型
        )
        
        # 启动会议
        start_conference(conference_id)
        
        # 重定向到会议页面
        return RedirectResponse(url=f"/conference/{conference_id}", status_code=303)
    except Exception as e:
        logger.error(f"Error in start_new_conference: {str(e)}")
        error_html = templates.get_template("error.html").render(
            request=request,
            error_title="会议创建失败",
            error_message=str(e),
            version=VERSION_INFO
        )
        return HTMLResponse(content=error_html)

# 管理特定会议
@app.get("/conference/{conference_id}", response_class=HTMLResponse)
async def manage_conference(request: Request, conference_id: str):
    try:
        conference = get_conference(conference_id)
        if not conference:
            return HTMLResponse("错误：会议ID不存在", status_code=404)
        
        # 确保获取所有代理列表，而不只是会议参与者
        all_agents = list_agents()
        
        # 从数据库获取当前阶段的对话历史
        conn = sqlite3.connect('conversations.db')
        cursor = conn.cursor()
        cursor.execute('SELECT agent_id, speech, timestamp FROM conversations WHERE conference_id = ? AND phase_id = ?', 
                       (conference_id, conference.current_phase_index))
        dialogue = [{"agent_id": row[0], "speech": row[1], "timestamp": row[2]} for row in cursor.fetchall()]
        conn.close()
        
        return templates.TemplateResponse("conference.html", {
            "request": request, 
            "conference": conference, 
            "agents": all_agents,  # 传递所有代理 
            "dialogue": dialogue
        })
    except Exception as e:
        return HTMLResponse(f"错误：{str(e)}", status_code=500)

# 对话记录保存和通知
async def save_dialogue_to_db(dialogue_entry, conference_id, phase_id):
    # 保存到数据库
    conn = sqlite3.connect('conversations.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO conversations (conference_id, phase_id, agent_id, speech, timestamp) VALUES (?, ?, ?, ?, ?)',
                    (conference_id, phase_id, dialogue_entry["agent_id"], dialogue_entry["speech"], dialogue_entry["timestamp"]))
        conn.commit()
    finally:
        conn.close()
    
    # 获取代理名称
    agent_name = get_agent_name_by_id(dialogue_entry["agent_id"]) or dialogue_entry["agent_id"]
    
    # 通过WebSocket发送通知
    await manager.send_dialogue({
        "agent_id": dialogue_entry["agent_id"],
        "agent_name": agent_name,
        "speech": dialogue_entry["speech"],
        "timestamp": dialogue_entry["timestamp"]
    }, conference_id)

# 对话监控线程
async def monitor_dialogue_file(conference_id, phase_id):
    dialogue_file = f"dialogue_history_{conference_id}_{phase_id}.json"
    last_size = 0
    last_count = 0
    
    while True:
        try:
            dialogue_history = []
            try:
                with open(dialogue_file, "r") as f:
                    dialogue_history = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                # 文件可能还不存在或格式不正确，继续等待
                await asyncio.sleep(1)
                continue
                
            # 如果有新的对话
            if len(dialogue_history) > last_count:
                # 只处理新增的对话
                for entry in dialogue_history[last_count:]:
                    # 确保entry包含必要的字段
                    if "agent_id" not in entry or "speech" not in entry:
                        print(f"警告：对话记录缺少必要字段: {entry}")
                        continue
                    
                    # 如果没有timestamp，添加当前时间
                    if "timestamp" not in entry:
                        entry["timestamp"] = datetime.now().isoformat()
                        print(f"警告：对话记录缺少timestamp字段，已自动添加")
                    
                    await save_dialogue_to_db(entry, conference_id, phase_id)
                last_count = len(dialogue_history)
        except Exception as e:
            print(f"监控对话文件时出错: {str(e)}")
        
        await asyncio.sleep(0.5)  # 每半秒检查一次

# 推进阶段
@app.post("/conference/{conference_id}/advance", response_class=HTMLResponse)
async def advance_conference_phase(request: Request, conference_id: str):
    try:
        advance_phase(conference_id)
        return await manage_conference(request, conference_id)
    except Exception as e:
        return HTMLResponse(f"错误：{str(e)}", status_code=500)

# 结束阶段并处理讨论
@app.post("/conference/{conference_id}/end_phase")
async def end_conference_phase(request: Request, conference_id: str, action: str = Form(None), 
                              agent_id: str = Form(None), question: str = Form(None)):
    try:
        conference = get_conference(conference_id)
        if not conference:
            return JSONResponse({"message": "错误：会议不存在", "success": False}, status_code=404)
            
        phase_id = conference.current_phase_index

        # 创建一个 dialogue_response 变量存储响应
        dialogue_response = None
        message = "处理失败，请重试"

        # 使用超时执行任务 - 防止 API 调用卡住
        async def run_with_timeout(func, *args, timeout=30):
            try:
                # 使用线程池执行阻塞操作
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(pool, func, *args),
                        timeout=timeout
                    )
                    
                # 处理不同类型的结果
                if isinstance(result, bool):
                    # 布尔值结果
                    return {"success": result, "result": None}
                elif isinstance(result, str) and (result.startswith("错误:") or result.startswith("讨论过程出错") or "失败" in result or "API" in result):
                    # 字符串形式的错误信息
                    return {"success": False, "error": result}
                else:
                    # 其他结果都视为成功
                    return {"success": True, "result": result}
                    
            except asyncio.TimeoutError:
                return {"success": False, "error": "操作超时，API 可能暂时不可用"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        # 根据不同的操作处理请求
        if action == "continue":
            message = "继续讨论"
            
            # 确保对话历史文件存在并包含最新的用户提问和代理回答
            dialogue_file = f"dialogue_history_{conference_id}_{phase_id}.json"
            try:
                # 首先从数据库获取所有对话记录
                conn = sqlite3.connect('conversations.db')
                cursor = conn.cursor()
                cursor.execute('SELECT agent_id, speech, timestamp FROM conversations WHERE conference_id = ? AND phase_id = ? ORDER BY timestamp',
                              (conference_id, phase_id))
                
                db_dialogue = []
                for row in cursor.fetchall():
                    agent_id, speech, timestamp = row
                    db_dialogue.append({
                        "agent_id": agent_id,
                        "speech": speech,
                        "timestamp": timestamp
                    })
                conn.close()
                
                # 保存到JSON文件，确保文件包含最新的对话记录
                if db_dialogue:
                    with open(dialogue_file, "w") as f:
                        json.dump(db_dialogue, f, indent=4)
                    print(f"已将 {len(db_dialogue)} 条对话记录写入文件 {dialogue_file}")
            except Exception as e:
                print(f"更新对话历史文件时出错: {str(e)}")
            
            # 启动对话监控任务
            monitor_task = asyncio.create_task(monitor_dialogue_file(conference_id, phase_id))
            dialogue_listeners[f"{conference_id}_{phase_id}"] = monitor_task
            
            try:
                # 执行讨论任务并等待结果
                discussion_result = await run_with_timeout(start_phase_discussion, conference_id, phase_id)
                if not discussion_result["success"]:
                    return JSONResponse({
                        "message": f"启动讨论失败: {discussion_result['error']}", 
                        "success": False,
                        "error_type": "API错误"
                    }, status_code=500)
            except Exception as e:
                return JSONResponse({
                    "message": f"启动讨论出错: {str(e)}", 
                    "success": False,
                    "error_type": "系统错误"
                }, status_code=500)
            
        elif action == "interrupt":
            interrupt_result = await run_with_timeout(user_intervene, conference_id, phase_id, "interrupt")
            if interrupt_result["success"]:
                message = "已中断讨论"
            else:
                return JSONResponse({
                    "message": f"中断讨论失败: {interrupt_result['error']}", 
                    "success": False
                }, status_code=500)
                
        elif action == "question":
            # 增强参数验证
            if not agent_id:
                return JSONResponse({
                    "message": "错误：提问时必须提供专家ID", 
                    "success": False
                }, status_code=400)
                
            if not question:
                return JSONResponse({
                    "message": "错误：提问时必须提供问题内容", 
                    "success": False
                }, status_code=400)
            
            # 验证专家ID是否存在
            agent = None
            try:
                from agent_db import get_agent
                agent = get_agent(agent_id)
                if not agent:
                    return JSONResponse({
                        "message": f"错误：专家ID '{agent_id}' 不存在", 
                        "success": False
                    }, status_code=400)
            except Exception as e:
                print(f"验证专家时出错: {str(e)}")
                # 即使验证失败也继续尝试，因为user_intervene会再次验证
                
            question_result = await run_with_timeout(
                user_intervene, conference_id, phase_id, "question", agent_id, question
            )
            
            if question_result["success"]:
                dialogue_response = question_result["result"]
                # 如果获取到专家名称，则在消息中显示
                agent_name = get_agent_name_by_id(agent_id) if 'get_agent_name_by_id' in globals() else agent_id
                
                # 手动将回答添加到对话历史数据库并通过WebSocket发送
                if dialogue_response and not isinstance(dialogue_response, bool):
                    timestamp = datetime.now().isoformat()
                    
                    # 先添加用户提问到数据库
                    conn = sqlite3.connect('conversations.db')
                    cursor = conn.cursor()
                    try:
                        # 保存用户提问
                        user_question = f"提问给 {agent_name}: {question}"
                        cursor.execute('INSERT INTO conversations (conference_id, phase_id, agent_id, speech, timestamp) VALUES (?, ?, ?, ?, ?)',
                                      (conference_id, phase_id, "用户", user_question, timestamp))
                        
                        # 保存专家回答
                        cursor.execute('INSERT INTO conversations (conference_id, phase_id, agent_id, speech, timestamp) VALUES (?, ?, ?, ?, ?)',
                                       (conference_id, phase_id, agent_id, dialogue_response, timestamp))
                        conn.commit()
                    finally:
                        conn.close()
                    
                    # 通过WebSocket发送用户提问
                    await manager.send_dialogue({
                        "agent_id": "用户",
                        "agent_name": "用户",
                        "speech": user_question,
                        "timestamp": timestamp
                    }, conference_id)
                    
                    # 通过WebSocket发送专家回答
                    await manager.send_dialogue({
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                        "speech": dialogue_response,
                        "timestamp": timestamp
                    }, conference_id)
                
                message = f"已向专家 {agent_name} ({agent_id}) 提问，并收到回复"
            else:
                return JSONResponse({
                    "message": f"提问失败: {question_result['error']}",
                    "success": False,
                    "fallback_response": f"由于API调用问题，无法获取 {agent_id} 的回答。请稍后再试。"
                }, status_code=500)
        else:
            return JSONResponse({"message": f"错误：无效的动作 '{action}'", "success": False}, status_code=400)

        # 尝试从文件加载对话历史
        dialogue_history = []
        dialogue_file = f"dialogue_history_{conference_id}_{phase_id}.json"
        try:
            with open(dialogue_file, "r") as f:
                dialogue_history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"警告：对话历史文件问题 {dialogue_file}: {str(e)}")
            # 如果文件不存在或格式错误，我们创建一个空的历史，而不是中断流程

        # 使用批量操作和事务优化数据库写入
        conn = sqlite3.connect('conversations.db')
        try:
            cursor = conn.cursor()
            
            # 先获取已存在的发言记录
            existing_speeches = set()
            cursor.execute('SELECT agent_id, speech FROM conversations WHERE conference_id = ? AND phase_id = ?',
                       (conference_id, phase_id))
            for row in cursor.fetchall():
                existing_speeches.add((row[0], row[1]))
            
            # 只插入新的发言
            entries_to_insert = []
            for entry in dialogue_history:
                speech_key = (entry["agent_id"], entry["speech"])
                if speech_key not in existing_speeches:
                    entries_to_insert.append(
                        (conference_id, phase_id, entry["agent_id"], entry["speech"], datetime.now().isoformat())
                    )
            
            if entries_to_insert:
                cursor.executemany(
                    'INSERT INTO conversations (conference_id, phase_id, agent_id, speech, timestamp) VALUES (?, ?, ?, ?, ?)',
                    entries_to_insert
                )
            conn.commit()
            print(f"已成功添加 {len(entries_to_insert)} 条新对话到数据库")
        except Exception as e:
            conn.rollback()
            print(f"错误：将对话保存到数据库时发生异常: {str(e)}")
            # 即使数据库操作失败，我们也继续处理，而不是抛出异常
        finally:
            conn.close()
            
        # 尝试结束阶段，但捕获可能的异常
        try:
            end_phase(conference_id)
        except Exception as e:
            print(f"警告：结束阶段时出错: {str(e)}")
            # 不要让这个错误中断响应
        
        # 返回JSON响应
        response_data = {
            "message": message,
            "success": True
        }
        
        if dialogue_response:
            response_data["dialogue"] = dialogue_response
            
        return JSONResponse(response_data)
            
    except Exception as e:
        return JSONResponse({
            "message": f"错误：{str(e)}", 
            "success": False,
            "error_type": type(e).__name__
        }, status_code=500)

# 结束整个会议
@app.post("/conference/{conference_id}/end", response_class=HTMLResponse)
async def end_entire_conference(request: Request, conference_id: str):
    try:
        end_conference(conference_id)
        return await home(request)
    except Exception as e:
        return HTMLResponse(f"错误：{str(e)}", status_code=500)

@app.delete("/api/conferences/{conference_id}")
async def delete_conference_endpoint(conference_id: str):
    try:
        # 检查会议是否存在
        conference = get_conference(conference_id)
        if not conference:
            return JSONResponse(status_code=404, 
                              content={"error": f"找不到会议 ID: {conference_id}"})
        
        # 删除会议
        delete_conference(conference_id)
        
        return {"message": f"会议 '{conference.title}' 已成功删除"}
    except Exception as e:
        return JSONResponse(status_code=500,
                          content={"error": f"删除会议时出错: {str(e)}"})
