from agent_db import get_agent, list_agents, get_random_agents
from conference_organizer import get_conference
import random
import json
from openai import OpenAI  # 导入 OpenAI 库以进行 API 调用
from dotenv import load_dotenv  # 导入 dotenv 以加载 .env 文件
import os
import time
import importlib
import re
from datetime import datetime
import shutil

# 从 .env 文件加载环境变量
load_dotenv()

# 支持的 API 提供商列表
SUPPORTED_PROVIDERS = [
    "oneapi", "openai", "anthropic", "gemini", "deepseek", 
    "siliconflow", "volcengine", "tencentcloud", "aliyun"
]

# 默认提供商，从环境变量读取
DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "oneapi")

# API 客户端缓存
api_clients = {}

# 初始化 API 客户端
def init_api_client(provider):
    """初始化特定提供商的 API 客户端"""
    if provider in api_clients:
        return api_clients[provider]
    
    if provider == "oneapi":
        api_key = os.getenv("ONEAPI_API_KEY")
        base_url = os.getenv("ONEAPI_BASE_URL", "https://api.oneapi.com/v1")
        if not api_key:
            print(f"警告: OneAPI 密钥未设置")
            return None
        client = OpenAI(api_key=api_key, base_url=base_url)
        api_clients[provider] = {"client": client, "type": "openai_compatible"}
        return api_clients[provider]
    
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if not api_key:
            print(f"警告: OpenAI 密钥未设置")
            return None
        client = OpenAI(api_key=api_key, base_url=base_url)
        api_clients[provider] = {"client": client, "type": "openai_compatible"}
        return api_clients[provider]
    
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print(f"警告: Anthropic 密钥未设置")
            return None
        try:
            # 这里使用条件导入，因为可能没有安装 anthropic 库
            anthropic = importlib.import_module("anthropic")
            client = anthropic.Anthropic(api_key=api_key)
            api_clients[provider] = {"client": client, "type": "anthropic"}
            return api_clients[provider]
        except (ImportError, ModuleNotFoundError):
            print(f"警告: Anthropic 库未安装，请使用 pip install anthropic 安装")
            return None
    
    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print(f"警告: Gemini 密钥未设置")
            return None
        try:
            # 使用条件导入 Google Generative AI 库
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            api_clients[provider] = {"client": genai, "type": "gemini"}
            return api_clients[provider]
        except (ImportError, ModuleNotFoundError):
            print(f"警告: Google Generative AI 库未安装，请使用 pip install google-generativeai 安装")
            return None
    
    elif provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        if not api_key:
            print(f"警告: DeepSeek 密钥未设置")
            return None
        client = OpenAI(api_key=api_key, base_url=base_url)
        api_clients[provider] = {"client": client, "type": "openai_compatible"}
        return api_clients[provider]
    
    elif provider == "siliconflow":
        api_key = os.getenv("SILICONFLOW_API_KEY")
        base_url = os.getenv("SILICONFLOW_BASE_URL", "https://api.ffa.chat/v1")
        if not api_key:
            print(f"警告: SiliconFlow 密钥未设置")
            return None
        client = OpenAI(api_key=api_key, base_url=base_url)
        api_clients[provider] = {"client": client, "type": "openai_compatible"}
        return api_clients[provider]
    
    elif provider == "volcengine":
        api_key = os.getenv("VOLCENGINE_API_KEY")
        base_url = os.getenv("VOLCENGINE_BASE_URL", "https://open.volcengineapi.com")
        if not api_key:
            print(f"警告: 火山引擎密钥未设置")
            return None
        # 火山引擎可能需要特殊的客户端，这里使用 OpenAI 兼容模式作为示例
        client = OpenAI(api_key=api_key, base_url=base_url)
        api_clients[provider] = {"client": client, "type": "openai_compatible"}
        return api_clients[provider]
    
    elif provider == "tencentcloud":
        secret_id = os.getenv("TENCENTCLOUD_SECRET_ID")
        secret_key = os.getenv("TENCENTCLOUD_SECRET_KEY")
        region = os.getenv("TENCENTCLOUD_REGION", "ap-beijing")
        if not secret_id or not secret_key:
            print(f"警告: 腾讯云密钥未设置")
            return None
        try:
            # 使用条件导入腾讯云 SDK
            from tencentcloud.common import credential
            from tencentcloud.common.profile.client_profile import ClientProfile
            from tencentcloud.common.profile.http_profile import HttpProfile
            from tencentcloud.hunyuan.v20230901 import hunyuan_client, models
            
            cred = credential.Credential(secret_id, secret_key)
            httpProfile = HttpProfile()
            clientProfile = ClientProfile()
            clientProfile.httpProfile = httpProfile
            client = hunyuan_client.HunyuanClient(cred, region, clientProfile)
            
            api_clients[provider] = {"client": client, "type": "tencentcloud", "models_module": models}
            return api_clients[provider]
        except (ImportError, ModuleNotFoundError):
            print(f"警告: 腾讯云 SDK 未安装，请使用 pip install tencentcloud-sdk-python 安装")
            return None
    
    elif provider == "aliyun":
        access_key_id = os.getenv("ALIYUN_ACCESS_KEY_ID")
        access_key_secret = os.getenv("ALIYUN_ACCESS_KEY_SECRET")
        region = os.getenv("ALIYUN_REGION", "cn-hangzhou")
        if not access_key_id or not access_key_secret:
            print(f"警告: 阿里云密钥未设置")
            return None
        try:
            # 使用条件导入阿里云 SDK
            from aliyunsdkcore.client import AcsClient
            from aliyunsdkcore.request import CommonRequest
            
            client = AcsClient(access_key_id, access_key_secret, region)
            api_clients[provider] = {"client": client, "type": "aliyun", "request_class": CommonRequest}
            return api_clients[provider]
        except (ImportError, ModuleNotFoundError):
            print(f"警告: 阿里云 SDK 未安装，请使用 pip install aliyun-python-sdk-core 安装")
            return None
    
    else:
        print(f"错误: 不支持的提供商 {provider}")
        return None

# 解析模型字符串，格式为 "provider:model_name"
def parse_model_string(model_string):
    """解析模型字符串，返回提供商和模型名称"""
    if ":" in model_string:
        provider, model_name = model_string.split(":", 1)
        if provider in SUPPORTED_PROVIDERS:
            return provider, model_name
    
    # 如果没有指定提供商或提供商不受支持，使用默认提供商
    return DEFAULT_PROVIDER, model_string

# 调用 API 生成回复
def call_llm_api(provider, model, prompt, max_tokens=None, temperature=None):
    """根据提供商调用相应的 LLM API"""
    if max_tokens is None:
        max_tokens = int(os.getenv("MAX_TOKENS", "4096"))
    if temperature is None:
        temperature = float(os.getenv("TEMPERATURE", "0.7"))
    
    # 获取 API 客户端
    api_client_info = init_api_client(provider)
    if not api_client_info:
        return f"错误：无法初始化 {provider} API 客户端"
    
    client_type = api_client_info["type"]
    client = api_client_info["client"]
    
    try:
        # 根据客户端类型调用不同的 API
        if client_type == "openai_compatible":
            # OpenAI 兼容接口 (OneAPI, OpenAI, DeepSeek, SiliconFlow 等)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        
        elif client_type == "anthropic":
            # Anthropic Claude API
            response = client.messages.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.content[0].text
        
        elif client_type == "gemini":
            # Google Gemini API
            model_obj = client.GenerativeModel(model)
            response = model_obj.generate_content(prompt)
            return response.text
        
        elif client_type == "tencentcloud":
            # 腾讯云 API
            models_module = api_client_info["models_module"]
            req = models_module.ChatCompletionsRequest()
            req.Messages = [{"Role": "user", "Content": prompt}]
            req.Model = model
            req.Temperature = temperature
            req.MaxTokens = max_tokens
            response = client.ChatCompletions(req)
            return response.Choices[0].Message.Content
        
        elif client_type == "aliyun":
            # 阿里云 API
            request_class = api_client_info["request_class"]
            request = request_class()
            request.set_domain('dashscope.aliyuncs.com')
            request.set_method('POST')
            request.set_protocol_type('https')
            request.set_version('2023-06-01')
            request.set_action_name('GenerateText')
            request.add_body_params('model', model)
            request.add_body_params('input', {
                'messages': [{'role': 'user', 'content': prompt}]
            })
            request.add_body_params('parameters', {
                'max_tokens': max_tokens,
                'temperature': temperature
            })
            response = client.do_action_with_exception(request)
            response_dict = json.loads(response)
            return response_dict['output']['text']
            
        else:
            return f"错误：不支持的客户端类型 {client_type}"
            
    except Exception as e:
        return f"API 调用错误：{str(e)}"

# 通过ID获取代理名称的辅助函数
def get_agent_name_by_id(agent_id):
    """通过代理ID获取代理名称"""
    agent = get_agent(agent_id)
    if agent:
        return agent.name
    return None

# 获取引用代理的名字而不是代号
def get_referenced_agent_name(text, agent_ids):
    """
    替换文本中的代理ID为对应的名称
    例如 "根据A004提到的..." 会变成 "根据Dr. Smith提到的..."
    """
    if not text:
        return text
        
    modified_text = text
    for agent_id in agent_ids:
        agent_name = get_agent_name_by_id(agent_id)
        if agent_name:
            # 使用正则表达式匹配A后接多个数字的模式，避免部分匹配
            pattern = r'\b' + re.escape(agent_id) + r'\b'
            modified_text = re.sub(pattern, agent_name, modified_text)
    
    return modified_text

# 使用 LLM API 生成代理发言
def generate_agent_speech(agent, phase_name, topic, previous_speech=None, is_follow_up=False, round_number=0):
    """使用指定的 LLM API 生成代理的发言。"""
    skills = ", ".join(agent.background_info.get("skills", []))
    mbti = agent.personality_traits.get("mbti", "未知")
    mood = agent.personality_traits.get("mood", "中性")
    style = agent.communication_style.get("style", "专业")
    tone = agent.communication_style.get("tone", "平静")
    
    # 特殊处理用户问题
    if previous_speech and previous_speech.get("agent_id") == "用户" and round_number == 99:
        user_question = previous_speech.get("speech", "")
        role_instruct = f"""你是一名专家，正在回答用户关于"{topic}"的问题。用户问题是："{user_question}"
        
你需要：
1. 直接切入问题核心，避免不必要的铺垫
2. 从你的专业角度提供具体、准确的回答
3. 如果问题涉及争议性内容，清晰说明不同观点
4. 确保回答深度和广度兼具，并提供明确的结论
5. 如合适，提供相关案例或数据支持你的观点

请确保回答简洁明了，重点突出，避免冗长。"""
        
        # 完整提示词
        prompt = f"""你是{agent.name}，一位MBTI性格为{mbti}的专家，擅长{skills}。你的沟通风格{style}，语调{tone}，情绪{mood}。

{role_instruct}

请用300-400字左右回答用户的问题，回答结束时提供一个简短的结论。"""

        print(f"正在为 {agent.name} 生成对用户问题的回答...")
        
        # 获取该代理的模型字符串
        agent_model = os.getenv(f"MODEL_{agent.agent_id}", os.getenv("DEFAULT_MODEL", f"{DEFAULT_PROVIDER}:gpt-3.5-turbo"))
        
        # 解析模型字符串，获取提供商和模型名称
        provider, model_name = parse_model_string(agent_model)
        
        try:
            print(f"使用 {provider} 的 {model_name} 模型生成回应...")
            answer = call_llm_api(
                provider, 
                model_name, 
                prompt, 
                max_tokens=int(os.getenv("MAX_TOKENS", "4000")),
                temperature=float(os.getenv("TEMPERATURE", "0.7"))
            )
            return answer
        except Exception as e:
            error_msg = f"错误：无法生成回应 - {str(e)}"
            print(error_msg)
            return error_msg
    
    # 根据阶段名称构建提示语
    elif "介绍" in phase_name:
        role_instruct = "你是一名专家，正在一个圆桌会议上进行自我介绍。请简短介绍自己的背景和你将如何贡献于讨论。"
    elif "讨论" in phase_name:
        if is_follow_up:
            role_instruct = f"""你是一名专家，参与了关于"{topic}"的多轮讨论，现在是第{round_number}轮。
你需要：
1. 直接回应之前专家的观点，指出你认同的部分和不同的见解
2. 引入新的思考角度或证据支持你的观点
3. 确保包含明确的结论和观点总结
4. 避免重复之前已经充分讨论的内容
5. 如果合适，提出1-2个有深度的问题引导下一阶段讨论
6. 结论部分应当清晰、简洁且有见地"""
        else:
            role_instruct = f"你是一名专家，正在一个圆桌会议上讨论"{topic}"。请提供你专业的见解和观点。"
    elif "分享" in phase_name:
        role_instruct = f"你是一名专家，正在一个圆桌会议上分享你关于"{topic}"的知识和经验。"
    elif "问答" in phase_name:
        role_instruct = f"你是一名专家，正在一个圆桌会议上回答关于"{topic}"的问题。"
    elif "风暴" in phase_name:
        role_instruct = f"你是一名专家，正在一个头脑风暴会议中为"{topic}"提供创新思路和解决方案。"
    elif "总结" in phase_name:
        role_instruct = f"你是一名专家，正在总结这次关于"{topic}"的讨论的主要观点和达成的共识。"
    else:
        role_instruct = f"你是一名专家，正在一个圆桌会议上讨论"{topic}"。"

    # 构建对话历史上下文
    context = ""
    if previous_speech:
        prev_agent_id = previous_speech.get("agent_id", "某位专家")
        prev_speech = previous_speech.get("speech", "")
        context = f"上一位发言的专家({prev_agent_id})说: {prev_speech}\n\n"
        
        # 如果是后续轮次，添加更多指导
        if is_follow_up:
            context += f"""
作为后续讨论的专家，你应该：
1. 简要参考并评价{prev_agent_id}的观点，而不是简单重复
2. 对其他专家提出的问题给出你的见解
3. 提供明确的论点和依据
4. 在发言结束时，提供一个清晰的"结论"部分，总结你的核心观点
5. 避免提出已经讨论过的基础问题，而是深入探讨更高层次的复杂问题

"""

    # 根据专家特性构建角色描述
    personality_desc = f"你是{agent.name}，一位MBTI性格为{mbti}的专家，擅长{skills}。你的沟通风格{style}，语调{tone}，情绪{mood}。"
    
    # 添加结论要求
    conclusion_req = ""
    if "讨论" in phase_name or "分享" in phase_name or "风暴" in phase_name:
        conclusion_req = "\n\n请在发言的最后部分添加一个明确的"结论"段落，简洁有力地总结你的核心观点。"
    
    # 根据轮次调整回复长度
    length_guide = ""
    if round_number == 0:
        length_guide = "请详细阐述你的观点，回应长度约400-600字。"
    elif is_follow_up:
        length_guide = "请简明扼要地表达你的观点，聚焦在新增价值上，回应长度约300-400字。"
    
    # 完整提示词
    prompt = f"""{personality_desc}

{role_instruct}

{context}

请基于你的专业背景和个性特点，围绕主题"{topic}"进行发言。{length_guide}{conclusion_req}"""

    print(f"正在为 {agent.name} 生成发言...")

    # 获取该代理的模型字符串
    agent_model = os.getenv(f"MODEL_{agent.agent_id}", os.getenv("DEFAULT_MODEL", f"{DEFAULT_PROVIDER}:gpt-3.5-turbo"))
    
    # 解析模型字符串，获取提供商和模型名称
    provider, model_name = parse_model_string(agent_model)
    
    # 调用 API，增加重试逻辑
    max_retries = int(os.getenv("MAX_RETRIES", "3"))
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            print(f"正在使用 {provider} 的 {model_name} 模型生成 {agent.name} 的回应...")
            speech = call_llm_api(
                provider, 
                model_name, 
                prompt, 
                max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
                temperature=float(os.getenv("TEMPERATURE", "0.7"))
            )
            
            # 检查返回的结果是否包含错误信息
            if speech and not speech.startswith("错误：") and not speech.startswith("API 调用错误："):
                # 获取所有参与者的代理ID用于替换
                conference_agents = [a.agent_id for a in list_agents()]
                return get_referenced_agent_name(speech, conference_agents)
            else:
                raise Exception(speech)
        except Exception as e:
            retry_count += 1
            print(f"API调用出错 (尝试 {retry_count}/{max_retries}): {str(e)}")
            if retry_count >= max_retries:
                # 所有重试都失败后，返回备用响应
                fallback_response = f"{agent.name}: 由于技术原因，无法使用 {provider} 的 {model_name} 模型获取完整回应。作为{mbti}类型的专家，我认为{topic}是一个重要话题，需要从多角度深入分析并提出具体解决方案。"
                print(f"使用备用回应: {fallback_response}")
                return fallback_response
            # 等待短暂时间后重试
            time.sleep(1)

# 开始阶段讨论的函数
def start_phase_discussion(conference_id, phase_id):
    """为会议中的特定阶段启动讨论。"""
    try:
        conference = get_conference(conference_id)
        if not conference:
            error_msg = f"未找到ID为 {conference_id} 的会议！"
            print(error_msg)
            return error_msg

        if phase_id < 0 or phase_id >= len(conference.agenda):
            error_msg = f"会议 '{conference.title}' 的阶段ID {phase_id} 无效！"
            print(error_msg)
            return error_msg

        current_phase = conference.agenda[phase_id]
        phase_name = current_phase["phase_name"]
        topics = current_phase["topics"]
        topic = topics[0]  # 为简单起见使用第一个话题

        print(f"开始 {phase_name} 讨论，主题为 {topic}...")
        agents = [get_agent(agent_id) for agent_id in conference.participant_agent_ids]
        if not agents or any(agent is None for agent in agents):
            error_msg = "错误：未找到有效的讨论代理！"
            print(error_msg)
            return error_msg

        dialogue_history = manage_turn_taking(conference_id, phase_name, topic, agents)
        
        # 如果对话历史为空可能表示出错了
        if not dialogue_history:
            error_msg = "错误：讨论过程未生成有效对话，可能是API调用失败"
            print(error_msg)
            return error_msg
            
        return True
    except Exception as e:
        error_msg = f"讨论过程出错: {str(e)}"
        print(error_msg)
        return error_msg

# 管理代理轮流发言的函数，带有动态响应
def manage_turn_taking(conference_id, phase_name, topic, agents):
    """管理轮流发言并实现动态代理交互。"""
    dialogue_history = []
    available_agents = agents.copy()
    random.shuffle(available_agents)  # 从随机顺序开始

    # 获取会议对象
    conference = get_conference(conference_id)
    if not conference:
        print(f"未找到ID为 {conference_id} 的会议！")
        return dialogue_history
        
    # 尝试从文件加载现有对话历史，包括之前的用户提问和代理回答
    history_dir = "dialogue_histories"
    history_file = os.path.join(history_dir, f"dialogue_history_{conference_id}_{conference.current_phase_index}.json")
    old_history_file = f"dialogue_history_{conference_id}_{conference.current_phase_index}.json"
    
    try:
        # 先尝试从新位置加载
        if os.path.exists(history_file):
            with open(history_file, "r", encoding='utf-8') as f:
                existing_history = json.load(f)
                if existing_history:
                    print(f"加载了 {len(existing_history)} 条已有对话记录，包括先前的提问和回答")
                    dialogue_history = existing_history
        # 再尝试从旧位置加载
        elif os.path.exists(old_history_file):
            with open(old_history_file, "r", encoding='utf-8') as f:
                existing_history = json.load(f)
                if existing_history:
                    print(f"从旧位置加载了 {len(existing_history)} 条已有对话记录，包括先前的提问和回答")
                    dialogue_history = existing_history
                    # 将旧文件移动到新位置
                    if not os.path.exists(history_dir):
                        os.makedirs(history_dir)
                    shutil.move(old_history_file, history_file)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"未找到现有对话历史或文件格式错误，将创建新的对话历史")

    # 从环境变量获取讨论轮数，默认为1
    discussion_rounds = int(os.getenv("DISCUSSION_ROUNDS", "1"))
    
    # 模拟讨论轮数
    for round_idx in range(discussion_rounds):
        print(f"开始第 {round_idx + 1} 轮讨论...")
        
        # 第一轮：所有代理都发言
        if round_idx == 0:
            for agent in available_agents:
                previous_speech = dialogue_history[-1] if dialogue_history else None
                
                # 如果previous_speech是用户提问，我们需要确保代理看到提问和回答的上下文
                if previous_speech and previous_speech.get("agent_id") == "用户" and len(dialogue_history) >= 2:
                    # 使用倒数第二条记录，也就是代理的回答
                    previous_speech = dialogue_history[-2]
                    
                speech = agent_speak(agent.agent_id, conference_id, phase_name, topic, previous_speech)
                timestamp = datetime.now().isoformat()
                dialogue_history.append({"agent_id": agent.agent_id, "speech": speech, "timestamp": timestamp})
                
                # 保存对话历史
                save_dialogue_history(dialogue_history, conference_id, conference.current_phase_index)
        
        # 第二轮及以后：只选择部分代理进行有针对性的回应
        else:
            # 计算每个代理的发言质量和信息量
            agent_scores = {}
            for agent in available_agents:
                # 找到该代理在上一轮的发言
                agent_speech = None
                for entry in reversed(dialogue_history):
                    if entry.get("agent_id") == agent.agent_id:
                        agent_speech = entry
                        break
                
                if agent_speech:
                    # 简单评分：发言长度、问题数量、结论清晰度
                    speech_text = agent_speech.get("speech", "")
                    length_score = min(len(speech_text) / 500, 1.0)  # 长度评分，最高1分
                    question_score = speech_text.count("?") * 0.2  # 每个问题0.2分
                    conclusion_score = 1.0 if "总结" in speech_text or "结论" in speech_text else 0
                    
                    # 计算总分
                    total_score = length_score + question_score + conclusion_score
                    agent_scores[agent.agent_id] = total_score
            
            # 选择得分最高的前50%代理参与下一轮
            num_to_select = max(2, len(available_agents) // 2)  # 至少选择2个代理
            selected_agents = []
            
            # 如果有分数，根据分数选择
            if agent_scores:
                sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
                selected_agent_ids = [agent_id for agent_id, _ in sorted_agents[:num_to_select]]
                selected_agents = [agent for agent in available_agents if agent.agent_id in selected_agent_ids]
            else:
                # 如果没有分数（异常情况），随机选择
                selected_agents = random.sample(available_agents, num_to_select)
            
            print(f"第 {round_idx + 1} 轮选择了 {len(selected_agents)} 个代理发言")
            
            # 让选中的代理发言，强调要对之前的观点进行回应和总结
            for agent in selected_agents:
                # 获取前一个不是当前代理的发言作为上下文
                previous_speeches = []
                for entry in reversed(dialogue_history):
                    if entry.get("agent_id") != agent.agent_id:
                        previous_speeches.append(entry)
                        if len(previous_speeches) >= 3:  # 获取最近3条其他代理的发言
                            break
                
                # 最近的一条发言
                previous_speech = previous_speeches[0] if previous_speeches else None
                
                # 指示代理提供更有针对性的回应和明确的结论
                speech = agent_speak(agent.agent_id, conference_id, phase_name, topic, previous_speech, 
                                    is_follow_up=True, round_number=round_idx+1)
                
                timestamp = datetime.now().isoformat()
                dialogue_history.append({"agent_id": agent.agent_id, "speech": speech, "timestamp": timestamp})
                
                # 保存对话历史
                save_dialogue_history(dialogue_history, conference_id, conference.current_phase_index)

    return dialogue_history

# 代理发言的函数
def agent_speak(agent_id, conference_id, phase_name, topic, previous_speech=None, is_follow_up=False, round_number=0):
    """为阶段生成并返回代理的发言。
    
    Args:
        agent_id: 代理ID
        conference_id: 会议ID
        phase_name: 阶段名称
        topic: 讨论主题
        previous_speech: 上一个发言，用于上下文
        is_follow_up: 是否是后续轮次的回应
        round_number: 当前轮次编号
    """
    agent = get_agent(agent_id)
    if not agent:
        return f"代理 {agent_id} 未找到！"
    
    conference = get_conference(conference_id)
    if not conference:
        return f"未找到ID为 {conference_id} 的会议！"

    return generate_agent_speech(agent, phase_name, topic, previous_speech, is_follow_up, round_number)

# 用户干预的函数
def user_intervene(conference_id, phase_id, user_action, target_agent_id=None, user_input=None):
    """允许用户中断或为特定阶段提问。"""
    conference = get_conference(conference_id)
    if not conference:
        print(f"未找到ID为 {conference_id} 的会议！")
        return False

    if phase_id < 0 or phase_id >= len(conference.agenda):
        print(f"阶段ID无效：{phase_id}！")
        return False

    # 获取当前阶段的主题和名称
    current_phase = conference.agenda[phase_id]
    topic = current_phase.get("topics", [""])[0]
    phase_name = current_phase.get("phase_name", "讨论")

    # 加载现有对话历史
    history_dir = "dialogue_histories"
    history_file = os.path.join(history_dir, f"dialogue_history_{conference_id}_{phase_id}.json")
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            dialogue_history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"找不到对话历史文件 {history_file}")
        dialogue_history = []

    # 处理用户动作
    if user_action == "interrupt":
        # 添加用户中断
        timestamp = datetime.now().isoformat()
        dialogue_history.append({"agent_id": "用户", "speech": f"用户打断：{user_input}", "timestamp": timestamp})
    elif user_action == "question":
        if target_agent_id and user_input:
            # 添加用户问题
            timestamp = datetime.now().isoformat()
            dialogue_history.append({"agent_id": "用户", "speech": f"提问给{target_agent_id}：{user_input}", "timestamp": timestamp})
            
            # 目标代理回答
            agent = get_agent(target_agent_id)
            if agent:
                # 创建一个特殊参数，指示代理这是对用户问题的回答
                response = generate_agent_speech(
                    agent, 
                    phase_name, 
                    topic, 
                    {"agent_id": "用户", "speech": user_input}, 
                    is_follow_up=True, 
                    round_number=99  # 特殊值表示这是用户问题
                )
                timestamp = datetime.now().isoformat()
                dialogue_history.append({"agent_id": target_agent_id, "speech": response, "timestamp": timestamp})
                
                # 更新对话历史
                save_dialogue_history(dialogue_history, conference_id, phase_id)
                return True
            else:
                print(f"找不到代理 {target_agent_id}！")
                return False
    else:
        print("无效的干预操作！")
        return False

def save_dialogue_history(dialogue_history, conference_id, phase_id):
    """保存对话历史到JSON文件"""
    # 确保dialogue_histories目录存在
    history_dir = "dialogue_histories"
    if not os.path.exists(history_dir):
        os.makedirs(history_dir)
        
    # 构建文件名
    filename = f"dialogue_history_{conference_id}_{phase_id}.json"
    file_path = os.path.join(history_dir, filename)
    
    # 保存对话历史
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(dialogue_history, f, ensure_ascii=False, indent=2)
    
    return filename

# 测试代码
if __name__ == "__main__":
    conference_id = "C001"
    print("=== 主题讨论阶段 ===")
    start_phase_discussion(conference_id, 0)
    user_intervene(conference_id, 0, "question", "A004", "AI伦理如何影响沟通？")
    user_intervene(conference_id, 0, "interrupt")
    print("\n=== 专家分享阶段 ===")
    start_phase_discussion(conference_id, 1)