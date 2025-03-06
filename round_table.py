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
def generate_agent_speech(agent, phase_name, topic, previous_speech=None):
    """使用指定的 LLM API 生成代理的发言。"""
    skills = ", ".join(agent.background_info.get("skills", []))
    mbti = agent.personality_traits.get("mbti", "未知")
    style = agent.communication_style.get("style", "中立")
    tone = agent.communication_style.get("tone", "中立")

    # 根据阶段类型和上下文构建提示词
    if phase_name == "主题讨论":
        if previous_speech:
            previous_agent_name = get_agent_name_by_id(previous_speech['agent_id']) or previous_speech['agent_id']
            
            # 检查前一条消息是否包含了用户问题的回答
            was_user_question_response = "提问给" in previous_speech.get('speech', '') or "用户" in previous_speech.get('speech', '')
            
            if was_user_question_response:
                prompt = f"""作为 {agent.name} (MBTI: {mbti}, 风格: {style})，请就 {topic} 进行深入讨论，同时考虑 {previous_agent_name} 刚才回答的用户提问。

你的回应需要：
1. 简明扼要地提及用户的提问以及 {previous_agent_name} 的核心回答观点
2. 从你的 {skills} 专业背景出发，对 {previous_agent_name} 的回答进行扩展或补充
3. 提供具体的例子、数据或案例支持你的观点
4. 分析这个问题的其他可能角度或解决方案
5. 提出一个深度思考问题，推动讨论向更深层次发展

请以 {tone} 的语调回答，避免空泛的表达和客套话。直接使用对方的名字 {previous_agent_name} 而不是代号。
限制在300字以内，保持内容丰富但简洁。请用中文回答。"""
            else:
                prompt = f"""作为 {agent.name} (MBTI: {mbti}, 风格: {style})，请回应 {previous_agent_name} 关于 {topic} 的观点。

你的回应需要：
1. 明确表达你对 {previous_agent_name} 观点的分析（不仅是简单的同意或反对）
2. 结合你的 {skills} 专业背景提供具体的例子、数据或案例
3. 提出1-2个具体且可行的解决方案或建议
4. 分析这些方案的可能影响和挑战
5. 提出一个深度思考问题，推动讨论向更深层次发展

请以 {tone} 的语调回答，避免空泛的表达和客套话。直接使用对方的名字 {previous_agent_name} 而不是代号。
限制在300字以内，保持内容丰富但简洁。请用中文回答。"""
        else:
            prompt = f"""作为 {agent.name} (MBTI: {mbti}, 风格: {style})，请就 {topic} 展开深度分析。

你的回应需要：
1. 简明扼要地解释为什么 {topic} 在当前背景下至关重要
2. 结合你的 {skills} 专业背景分析其中2-3个关键挑战或机遇
3. 提供具体的数据、案例或研究结果支持你的观点
4. 提出1-2个具体且可行的解决方案或建议
5. 分析这些方案的可能影响和实施难点

请以 {tone} 的语调回答，避免空泛的表达和客套话。
限制在300字以内，保持内容丰富但简洁。请用中文回答。"""
    elif phase_name == "专家分享":
        if previous_speech and "专家" in previous_speech["speech"].lower():
            previous_agent_name = get_agent_name_by_id(previous_speech['agent_id']) or previous_speech['agent_id']
            prompt = f"""作为 {agent.name} (MBTI: {mbti}, 风格: {style})，请在 {previous_agent_name} 关于 {topic} 的专业分享基础上进行扩展。

你的回应需要：
1. 简明扼要地总结 {previous_agent_name} 的核心观点（不要过于冗长）
2. 从你的 {skills} 专业角度提供补充视角或不同的解读
3. 分享1-2个相关但 {previous_agent_name} 未提及的关键洞见
4. 提供具体的案例、研究或数据支持你的观点
5. 指出当前领域内存在的争议或未解问题

请以 {tone} 的语调回答，确保内容既有专业深度又通俗易懂。直接使用对方的名字 {previous_agent_name} 而不是代号。
限制在300字以内，保持内容丰富但简洁。请用中文回答。"""
        else:
            prompt = f"""作为 {agent.name} (MBTI: {mbti}, 风格: {style})，请就 {topic} 进行专业性分享。

你的分享需要：
1. 开门见山地指出 {topic} 中最被误解或忽视的1-2个关键方面
2. 结合你的 {skills} 专业背景，分享2-3个独到的专业见解
3. 提供具体的案例、研究数据或实践经验支持你的论点
4. 分析当前领域内的主要争议或发展趋势
5. 提出对未来发展的预测或建议

请以 {tone} 的语调回答，确保内容既有专业深度又通俗易懂。
限制在300字以内，保持内容丰富但简洁。请用中文回答。"""
    elif phase_name == "问答":
        prompt = f"""作为 {agent.name} (MBTI: {mbti}, 风格: {style})，请就 {topic} 相关问题提供专业回答。

你的回应需要：
1. 直接切入问题核心，避免不必要的铺垫
2. 基于你的 {skills} 专业知识提供准确、全面的解释
3. 提供具体的例子、数据或案例支持你的回答
4. 分析不同观点或方法的优缺点
5. 在适当的情况下，承认领域内的不确定性或知识局限

请以 {tone} 的语调回答，确保内容既权威又易于理解。
限制在300字以内，保持内容丰富但简洁。请用中文回答。"""
    else:
        prompt = f"""作为 {agent.name} (MBTI: {mbti}, 风格: {style})，请就 {topic} 提供深入评论。

你的评论需要：
1. 开门见山地指出 {topic} 的核心价值或挑战
2. 结合你的 {skills} 专业背景提供独特视角
3. 引用相关研究、数据或案例支持你的观点
4. 分析当前主流观点的局限性或盲点
5. 提出创新性的思考方向或解决思路

请以 {tone} 的语调回答，避免空泛的表达和客套话。
限制在300字以内，保持内容丰富但简洁。请用中文回答。"""

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
    history_file = f"dialogue_history_{conference_id}_{conference.current_phase_index}.json"
    try:
        with open(history_file, "r") as f:
            existing_history = json.load(f)
            if existing_history:
                print(f"加载了 {len(existing_history)} 条已有对话记录，包括先前的提问和回答")
                dialogue_history = existing_history
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"未找到现有对话历史或文件格式错误，将创建新的对话历史")

    # 模拟两轮讨论
    for _ in range(int(os.getenv("DISCUSSION_ROUNDS", "2"))):
        for agent in available_agents:
            previous_speech = dialogue_history[-1] if dialogue_history else None
            
            # 如果previous_speech是用户提问，我们需要确保代理看到提问和回答的上下文
            if previous_speech and previous_speech.get("agent_id") == "用户" and len(dialogue_history) >= 2:
                # 使用倒数第二条记录，也就是代理的回答
                previous_speech = dialogue_history[-2]
                
            speech = agent_speak(agent.agent_id, conference_id, phase_name, topic, previous_speech)
            timestamp = datetime.now().isoformat()
            dialogue_history.append({"agent_id": agent.agent_id, "speech": speech, "timestamp": timestamp})
            
            # 将对话历史保存到文件，用于实时流式传输
            with open(f"dialogue_history_{conference_id}_{conference.current_phase_index}.json", "w") as f:
                json.dump(dialogue_history, f, indent=4)
                
            print(speech)
        random.shuffle(available_agents)  # 为下一轮重新洗牌

    return dialogue_history

# 代理发言的函数
def agent_speak(agent_id, conference_id, phase_name, topic, previous_speech=None):
    """为阶段生成并返回代理的发言。"""
    agent = get_agent(agent_id)
    if not agent:
        return f"代理 {agent_id} 未找到！"
    
    conference = get_conference(conference_id)
    if not conference:
        return f"未找到ID为 {conference_id} 的会议！"

    return generate_agent_speech(agent, phase_name, topic, previous_speech)

# 用户干预的函数
def user_intervene(conference_id, phase_id, user_action, target_agent_id=None, user_input=None):
    """允许用户中断或为特定阶段提问。"""
    conference = get_conference(conference_id)
    if not conference:
        print(f"未找到ID为 {conference_id} 的会议！")
        return False

    if phase_id < 0 or phase_id >= len(conference.agenda):
        print(f"会议 '{conference.title}' 的阶段ID {phase_id} 无效！")
        return False

    current_phase = conference.agenda[phase_id]
    topic = current_phase["topics"][0]
    phase_name = current_phase["phase_name"]

    if user_action == "interrupt":
        print(f"用户中断了关于 {topic} 的讨论。")
        return True
    elif user_action == "question" and target_agent_id and user_input:
        agent = get_agent(target_agent_id)
        if not agent:
            print(f"代理 {target_agent_id} 未找到！")
            return False

        # 获取该代理的模型字符串
        agent_model = os.getenv(f"MODEL_{target_agent_id}", os.getenv("DEFAULT_MODEL", f"{DEFAULT_PROVIDER}:gpt-3.5-turbo"))
        
        # 解析模型字符串，获取提供商和模型名称
        provider, model_name = parse_model_string(agent_model)
        
        prompt = f"""作为 {agent.name}，请回答用户关于 {topic} 的问题："{user_input}"

你的回答需要：
1. 直接切入问题核心，避免不必要的铺垫
2. 基于你的 {', '.join(agent.background_info.get('skills', []))} 专业背景，提供具体且全面的分析
3. 引用相关研究、数据或案例支持你的观点
4. 如可能，提出1-2个具体且可行的解决方案或建议
5. 坦诚讨论可能的挑战、限制或不同观点

请以 {agent.communication_style.get('tone', '中立')} 的语调回答，保持专业性的同时确保内容通俗易懂。
请用中文回答，引用其他代理时请使用他们的名字而不是代号。
限制在300字以内，保持内容丰富但简洁。"""
        
        try:
            print(f"正在使用 {provider} 的 {model_name} 模型生成 {agent.name} 的回应...")
            answer = call_llm_api(
                provider, 
                model_name, 
                prompt, 
                max_tokens=int(os.getenv("MAX_TOKENS", "4000")),
                temperature=float(os.getenv("TEMPERATURE", "0.7"))
            )
            
            # 检查返回的结果是否包含错误信息
            if answer.startswith("错误：") or answer.startswith("API 调用错误："):
                raise Exception(answer)
                
            # 替换代理ID为对应名称
            conference_agents = [a.agent_id for a in list_agents()]
            answer = get_referenced_agent_name(answer, conference_agents)
        except Exception as e:
            answer = f"错误：无法生成回应 ({str(e)})"

        print(f"用户向 {agent.name} 提问：'{user_input}'")
        print(f"{agent.name} 回应：{answer}")

        # 添加到对话历史
        history_file = f"dialogue_history_{conference_id}_{phase_id}.json"
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            history = []
        
        # 添加用户提问作为对话历史的一部分
        timestamp = datetime.now().isoformat()
        user_question_entry = {
            "agent_id": "用户", 
            "speech": f"提问给 {agent.name}: {user_input}", 
            "timestamp": timestamp
        }
        history.append(user_question_entry)
        
        # 添加代理回答
        timestamp = datetime.now().isoformat()
        history.append({"agent_id": target_agent_id, "speech": answer, "timestamp": timestamp})
        
        with open(history_file, "w") as f:
            json.dump(history, f, indent=4)
        return answer
    else:
        print("无效的干预操作！")
        return False

# 测试代码
if __name__ == "__main__":
    conference_id = "C001"
    print("=== 主题讨论阶段 ===")
    start_phase_discussion(conference_id, 0)
    user_intervene(conference_id, 0, "question", "A004", "AI伦理如何影响沟通？")
    user_intervene(conference_id, 0, "interrupt")
    print("\n=== 专家分享阶段 ===")
    start_phase_discussion(conference_id, 1)