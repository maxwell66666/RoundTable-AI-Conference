from fastapi import FastAPI, Request, Form, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import sqlite3
import json
from round_table import start_phase_discussion, user_intervene, get_agent_name_by_id
from conference_organizer import (
    create_conference, start_conference, advance_phase, 
    end_phase, end_conference, get_conference, 
    list_conferences, init_conference_db
)
from agent_db import list_agents, init_agent_db
from datetime import datetime
import asyncio
import concurrent.futures
from typing import List, Dict, Any
from starlette.websockets import WebSocketState
import threading
from version import get_version, get_version_info
from db_migrations import run_migrations

app = FastAPI(title="RoundTable对话系统", version=get_version())

# 挂载静态文件目录（用于CSS等静态资源）
app.mount("/static", StaticFiles(directory="static"), name="static")

# 设置Jinja2模板
templates = Jinja2Templates(directory="templates")

# 版本信息
VERSION_INFO = get_version_info()

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
    agents = list_agents()
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "conferences": conferences, 
        "agents": agents,
        "version": VERSION_INFO
    })

# 启动新会议
@app.post("/start_conference", response_class=HTMLResponse)
async def start_new_conference(request: Request, agent_ids: str = Form(...)):
    try:
        # 从表单数据获取议程
        form_data = await request.form()
        agenda_text = form_data.get('agenda')
        custom_title = form_data.get('conference_title', '').strip()
        
        if not agenda_text:
            raise ValueError("议程数据不能为空")
            
        try:
            agenda = json.loads(agenda_text)
        except json.JSONDecodeError:
            raise ValueError("议程格式无效，请提供有效的JSON")
            
        # 验证议程文件格式
        for phase in agenda:
            if "topics" not in phase or not phase["topics"]:
                raise ValueError("每个阶段必须包含非空的 topics 字段")
                
        # 生成会议标题：使用日期和首个主题
        current_date = datetime.now().strftime("%Y-%m-%d")
        main_topic = agenda[0]["topics"][0] if agenda and "topics" in agenda[0] and agenda[0]["topics"] else "未指定主题"
        
        # 如果用户提供了标题，则使用用户的标题，否则生成标题
        if custom_title:
            title = custom_title
        else:
            title = f"{current_date} - {main_topic}"
            
        agent_ids_list = agent_ids.split(',')
        conference_id = f"C{len(list_conferences()) + 1:03d}"
        conference = create_conference(conference_id, title, agenda, agent_ids_list)
        start_conference(conference_id)
        return templates.TemplateResponse("conference.html", {"request": request, "conference": conference})
    except json.JSONDecodeError:
        return HTMLResponse("错误：议程格式无效，请提供有效的JSON", status_code=400)
    except ValueError as e:
        return HTMLResponse(f"错误：{str(e)}", status_code=400)

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
            
            # 在后台处理讨论
            asyncio.create_task(run_with_timeout(start_phase_discussion, conference_id, phase_id))
            
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
                    "message": "错误：提问时必须提供代理ID", 
                    "success": False
                }, status_code=400)
                
            if not question:
                return JSONResponse({
                    "message": "错误：提问时必须提供问题内容", 
                    "success": False
                }, status_code=400)
            
            # 验证代理ID是否存在
            agent = None
            try:
                from agent_db import get_agent
                agent = get_agent(agent_id)
                if not agent:
                    return JSONResponse({
                        "message": f"错误：代理ID '{agent_id}' 不存在", 
                        "success": False
                    }, status_code=400)
            except Exception as e:
                print(f"验证代理时出错: {str(e)}")
                # 即使验证失败也继续尝试，因为user_intervene会再次验证
                
            question_result = await run_with_timeout(
                user_intervene, conference_id, phase_id, "question", agent_id, question
            )
            
            if question_result["success"]:
                dialogue_response = question_result["result"]
                # 如果获取到代理名称，则在消息中显示
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
                        
                        # 保存代理回答
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
                    
                    # 通过WebSocket发送代理回答
                    await manager.send_dialogue({
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                        "speech": dialogue_response,
                        "timestamp": timestamp
                    }, conference_id)
                
                message = f"已向代理 {agent_name} ({agent_id}) 提问，并收到回复"
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
