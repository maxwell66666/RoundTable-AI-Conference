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
import requests

# 从 .env 文件加载环境变量
load_dotenv()

# 支持的 API 提供商列表
SUPPORTED_PROVIDERS = [
    "oneapi", "openai", "anthropic", "gemini", "deepseek", 
    "siliconflow", "volcengine", "tencentcloud", "aliyun", "openrouter"
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
        base_url = os.getenv("ONEAPI_BASE_URL", "https://api.ffa.chat/v1")
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
        base_url = os.getenv("VOLCENGINE_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
        if not api_key:
            print(f"警告: 火山引擎密钥未设置")
            return None
        # 火山引擎使用OpenAI兼容客户端，添加重试和超时配置
        print(f"初始化火山引擎API客户端，使用base_url: {base_url}")
        client = OpenAI(
            api_key=api_key, 
            base_url=base_url,
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            timeout=float(os.getenv("API_TIMEOUT", "30"))
        )
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
    
    elif provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        if not api_key:
            print(f"警告: OpenRouter 密钥未设置")
            return None
        # OpenRouter使用OpenAI兼容客户端，添加重试和超时配置
        print(f"初始化OpenRouter API客户端，使用base_url: {base_url}")
        client = OpenAI(
            api_key=api_key, 
            base_url=base_url,
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            timeout=float(os.getenv("API_TIMEOUT", "30"))
        )
        api_clients[provider] = {"client": client, "type": "openai_compatible"}
        return api_clients[provider]
    
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
    
    # 获取API超时设置
    api_timeout = int(os.getenv("API_TIMEOUT", "30"))
    
    # 获取 API 客户端
    api_client_info = init_api_client(provider)
    if not api_client_info:
        return f"错误：无法初始化 {provider} API 客户端"
    
    client_type = api_client_info["type"]
    client = api_client_info["client"]
    
    try:
        # 根据客户端类型调用不同的 API
        if client_type == "openai_compatible":
            # OpenAI 兼容接口 (OneAPI, OpenAI, DeepSeek, SiliconFlow, OpenRouter 等)
            print(f"调用 {provider} API，模型: {model}，超时: {api_timeout}秒")
            
            # 检查是否是通过OneAPI调用Gemini模型
            is_gemini_via_oneapi = provider == "oneapi" and "gemini" in model.lower()
            
            # 如果是通过OneAPI调用Gemini模型，添加强制中文输出的指令
            if is_gemini_via_oneapi:
                enhanced_prompt = f"""
{prompt}

请用中文回答上述问题。即使问题是英文的，也请用中文回答。
Your response MUST be in Chinese. Even if the question is in English, please respond in Chinese only.
"""
            else:
                enhanced_prompt = prompt
            
            try:
                # 为OpenRouter添加特殊处理
                if provider == "openrouter":
                    # OpenRouter需要额外的HTTP头信息
                    headers = {
                        "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "https://github.com/yourusername/RoundTable"),
                        "X-Title": os.getenv("OPENROUTER_TITLE", "RoundTable AI Conference")
                    }
                    
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": enhanced_prompt}],
                        max_tokens=max_tokens,
                        temperature=temperature,
                        timeout=api_timeout,
                        extra_headers=headers  # 添加OpenRouter所需的额外头信息
                    )
                else:
                    # 其他OpenAI兼容接口
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": enhanced_prompt}],
                        max_tokens=max_tokens,
                        temperature=temperature,
                        timeout=api_timeout
                    )
                return response.choices[0].message.content.strip()
            except Exception as e:
                error_msg = str(e)
                print(f"API调用错误 ({provider}:{model}): {error_msg}")
                # 检查是否是超时错误
                if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                    return f"API 调用错误：请求超时 ({api_timeout}秒)，请检查网络连接或增加超时时间"
                # 检查是否是认证错误
                elif "auth" in error_msg.lower() or "key" in error_msg.lower() or "unauthorized" in error_msg.lower():
                    return f"API 调用错误：认证失败，请检查API密钥是否正确"
                # 检查是否是模型不存在错误
                elif "model" in error_msg.lower() and ("not found" in error_msg.lower() or "doesn't exist" in error_msg.lower()):
                    return f"API 调用错误：模型 '{model}' 不存在或不可用"
                else:
                    return f"API 调用错误：{error_msg}"
        
        elif client_type == "anthropic":
            # Anthropic Claude API
            response = client.messages.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=api_timeout  # 添加超时设置
            )
            return response.content[0].text
        
        elif client_type == "gemini":
            # Google Gemini API
            model_obj = client.GenerativeModel(model)
            
            # 为Gemini模型添加强制中文输出的指令
            enhanced_prompt = f"""
{prompt}

请用中文回答上述问题。即使问题是英文的，也请用中文回答。
Your response MUST be in Chinese. Even if the question is in English, please respond in Chinese only.
"""
            response = model_obj.generate_content(enhanced_prompt)
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
        error_msg = str(e)
        print(f"API调用过程中出现异常: {error_msg}")
        return f"错误：API调用过程中出现异常 - {error_msg}"

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

# 搜索最新信息的函数
def search_latest_info(topic, skills=None):
    """
    搜索与主题相关的最新信息
    
    参数:
        topic: 搜索主题
        skills: 技能列表，用于优化搜索查询
    
    返回:
        格式化后的搜索结果字符串
    """
    try:
        # 导入搜索引擎模块
        from search_engines import search_latest_info_with_engine
        
        # 从环境变量获取搜索引擎名称，默认使用tavily
        engine_name = os.getenv("SEARCH_ENGINE", "tavily")
        
        # 从环境变量获取最大结果数
        max_results = int(os.getenv("SEARCH_MAX_RESULTS", "5"))
        
        print(f"正在使用 {engine_name} 搜索关于 '{topic}' 的最新信息...")
        
        # 调用搜索引擎模块的函数
        return search_latest_info_with_engine(
            topic=topic,
            skills=skills,
            engine_name=engine_name,
            max_results=max_results
        )
    except Exception as e:
        # 如果搜索失败，返回错误信息
        error_msg = f"搜索时发生错误: {str(e)}"
        print(error_msg)
        
        # 返回一个基本的回退信息
        current_date = datetime.now().strftime("%Y年%m月%d日")
        return f"""搜索时间: {current_date}

很抱歉，在搜索"{topic}"相关信息时遇到了技术问题。

建议:
1. 请检查网络连接
2. 确认搜索引擎配置是否正确
3. 尝试使用不同的搜索引擎或关键词

错误详情: {str(e)}"""

# 使用 LLM API 生成代理发言
def generate_agent_speech(agent, phase_name, topic, previous_speech=None, search_results=None):
    """使用指定的LLM API 生成代理的发言"""
    skills = ", ".join(agent.background_info.get("skills", []))
    mbti = agent.personality_traits.get("mbti", "未知")
    style = agent.communication_style.get("style", "中立")
    tone = agent.communication_style.get("tone", "中立")

    # 如果没有提供搜索结果，则进行搜索
    # 注意：在新的对话流程中，主持人会提供搜索结果，其他专家应该使用主持人的搜索结果
    if search_results is None:
        # 从环境变量获取是否启用搜索
        enable_search = os.getenv("ENABLE_SEARCH", "true").lower() == "true"
        
        if enable_search:
            # 从环境变量获取搜索引擎，默认使用tavily
            search_engine = os.getenv("SEARCH_ENGINE", "tavily")
            print(f"为 {agent.name} 使用 {search_engine} 搜索关于 '{topic}' 的最新信息...")
            latest_info = search_latest_info(topic, skills)
        else:
            latest_info = f"搜索功能已禁用。请基于您的专业知识和理解来讨论主题：{topic}"
    else:
        # 使用传递的搜索结果
        latest_info = search_results
        print(f"为 {agent.name} 使用已提供的搜索结果")
    
    print(f"为 {agent.name} 使用的最新信息: {latest_info[:100]}..." if len(latest_info) > 100 else latest_info)

    # 根据阶段类型和上下文构建提示词
    if phase_name == "主题讨论":
        # 主题讨论阶段
        if previous_speech:
            # 获取上一位发言者的名字
            previous_agent_id = previous_speech.get('agent_id', '')
            previous_agent_name = get_agent_name_by_id(previous_agent_id) or previous_agent_id
            
            prompt = f"""你是一个名为{agent.name}的AI代理，正在参加一个圆桌会议。
你的MBTI类型是{mbti}，你的沟通风格是{style}，语气{tone}。
你的专业技能包括: {skills}

以下是关于主题"{topic}"的最新信息:
{latest_info}

会议上一位发言者{previous_agent_name}说:
{previous_speech}

请你以{agent.name}的身份，根据你的MBTI类型、沟通风格和专业背景，对{previous_agent_name}的观点进行回应。
在回应中，请引用最新的相关信息，并结合你的专业知识提供深入见解。
回应应当体现你的性格特点和沟通风格，语气应为{tone}。

重要要求:
1. 必须直接称呼上一位发言者为"{previous_agent_name}"，不要使用代号如"A001"
2. 必须对{previous_agent_name}的观点进行批判性思考，提出不同角度的见解或补充
3. 必须提出1个具体可行的解决方案或行动建议
4. 必须在发言结尾给出明确的结论
5. 只引用可验证的事实，避免编造或夸大信息
6. 如果不确定某个信息，请明确表示这是你的推测

回复格式要求:
1. 不要使用Markdown格式
2. 不要包含标题
3. 不要在开头介绍自己
4. 直接以{agent.name}的身份开始发言，可以先称呼{previous_agent_name}
5. 回应长度必须控制在200字以内
6. 必须使用中文回答，即使问题是英文的，也请用中文回答
7. 语言必须简洁、精确且富有洞察力
"""
        else:
            prompt = f"""你是一个名为{agent.name}的AI代理，正在参加一个圆桌会议。
你的MBTI类型是{mbti}，你的沟通风格是{style}，语气{tone}。
你的专业技能包括: {skills}

以下是关于主题"{topic}"的最新信息:
{latest_info}

请你以{agent.name}的身份，根据你的MBTI类型、沟通风格和专业背景，对主题"{topic}"发表看法。
在发言中，请引用最新的相关信息，并结合你的专业知识提供深入见解。
发言应当体现你的性格特点和沟通风格，语气应为{tone}。

重要要求:
1. 必须提出1个具体可行的解决方案或行动建议
2. 必须在发言结尾给出明确的结论
3. 只引用可验证的事实，避免编造或夸大信息
4. 如果不确定某个信息，请明确表示这是你的推测
5. 分析问题时要从多个角度思考

回复格式要求:
1. 不要使用Markdown格式
2. 不要包含标题
3. 不要在开头介绍自己
4. 直接以{agent.name}的身份开始发言
5. 发言长度必须控制在200字以内
6. 必须使用中文回答，即使问题是英文的，也请用中文回答
7. 语言必须简洁、精确且富有洞察力
"""
    elif phase_name == "专家分享":
        if previous_speech and "专家" in previous_speech["speech"].lower():
            previous_agent_name = get_agent_name_by_id(previous_speech['agent_id']) or previous_speech['agent_id']
            prompt = f"""作为 {agent.name}，你是{agent.background_info["field"]}领域的顶尖专家，请对{previous_agent_name}关于"{topic}"的观点进行深度剖析和专业延展。

你的MBTI类型是{mbti}，沟通风格是{style}，语气{tone}。
你的专业技能包括: {skills}

以下是关于该主题的最新信息，请在回答中适当参考：
{latest_info}

专业回应要求:
1. 必须以"{previous_agent_name}提到的..."开头，精准提炼其核心观点(1句话)
2. 必须明确指出{previous_agent_name}观点中的1个优点和1个局限或盲点
3. 必须从你的专业领域出发，提供1个{previous_agent_name}未提及的关键洞见
4. 必须提出1个极具操作性的解决方案
5. 必须在结尾给出极具价值的行动建议总结(1-2点)

回复格式要求:
1. 不要使用Markdown格式
2. 不要包含标题
3. 不要在开头介绍自己
4. 直接以{agent.name}的身份开始发言，先称呼{previous_agent_name}
5. 回应长度必须控制在200字以内
6. 必须使用中文回答
7. 语言必须简洁、精确且富有洞察力
"""
        else:
            prompt = f"""作为 {agent.name}，你是{agent.background_info["field"]}领域的顶尖专家，请就"{topic}"提供极具洞察力、前瞻性和变革性的专业评论。

你的MBTI类型是{mbti}，沟通风格是{style}，语气{tone}。
你的专业技能包括: {skills}

以下是关于该主题的最新信息，请在回答中适当参考：
{latest_info}

专业评论要求:
1. 必须开门见山地指出"{topic}"的核心本质和1-2个关键维度
2. 必须从你的专业角度提供1-2个突破性见解
3. 必须提出1个极具创新性的解决方案
4. 必须在结尾给出极具前瞻性的行动建议总结(1-2点)

回复格式要求:
1. 不要使用Markdown格式
2. 不要包含标题
3. 不要在开头介绍自己
4. 直接以{agent.name}的身份开始发言
5. 回应长度必须控制在200字以内
6. 必须使用中文回答
7. 语言必须简洁、精确且富有洞察力
"""
    elif phase_name == "问答":
        prompt = f"""作为 {agent.name}，你是{agent.background_info["field"]}领域的顶尖专家，请就"{topic}"相关问题提供极具深度、权威性和实用价值的专业解答。

你的MBTI类型是{mbti}，沟通风格是{style}，语气{tone}。
你的专业技能包括: {skills}

以下是关于该主题的最新信息，请在回答中适当参考：
{latest_info}

专业解答要求:
1. 必须立即切入问题核心，用1句话精准定义问题的本质
2. 必须提供简洁的专业分析，包括问题的根本原因和影响因素
3. 必须提出1-2个极具操作性的解决方案
4. 必须在结尾给出极具价值的行动建议总结(1-2点)

回复格式要求:
1. 不要使用Markdown格式
2. 不要包含标题
3. 不要在开头介绍自己
4. 直接以{agent.name}的身份开始发言
5. 回应长度必须控制在200字以内
6. 必须使用中文回答
7. 语言必须简洁、精确且富有洞察力
"""
    else:
        prompt = f"""作为 {agent.name}，你是{agent.background_info["field"]}领域的顶尖专家，请就"{topic}"提供极具洞察力、前瞻性和变革性的专业评论。

你的MBTI类型是{mbti}，沟通风格是{style}，语气{tone}。
你的专业技能包括: {skills}

以下是关于该主题的最新信息，请在回答中适当参考：
{latest_info}

专业评论要求:
1. 必须开门见山地指出"{topic}"的核心本质和1-2个关键维度
2. 必须从你的专业角度提供1-2个突破性见解
3. 必须提出1个极具创新性的解决方案
4. 必须在结尾给出极具前瞻性的行动建议总结(1-2点)

回复格式要求:
1. 不要使用Markdown格式
2. 不要包含标题
3. 不要在开头介绍自己
4. 直接以{agent.name}的身份开始发言
5. 回应长度必须控制在200字以内
6. 必须使用中文回答
7. 语言必须简洁、精确且富有洞察力
"""

    # 获取该代理的模型字符串
    agent_model = os.getenv(f"MODEL_{agent.agent_id}", os.getenv("DEFAULT_MODEL", f"{DEFAULT_PROVIDER}:gpt-3.5-turbo"))
    
    # 解析模型字符串，获取提供商和模型名称
    provider, model_name = parse_model_string(agent_model)
    
    # 调用 API，增加重试逻辑
    max_retries = int(os.getenv("MAX_RETRIES", "3"))
    retry_count = 0
    retry_delay = 2  # 初始重试延迟（秒）
    
    while retry_count < max_retries:
        try:
            print(f"正在使用 {provider} 的 {model_name} 模型生成 {agent.name} 的回应... (尝试 {retry_count+1}/{max_retries})")
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
            error_msg = str(e)
            print(f"API调用出错 (尝试 {retry_count}/{max_retries}): {error_msg}")
            
            if retry_count >= max_retries:
                # 所有重试都失败后，返回备用响应
                fallback_response = f"{agent.name}: 由于技术原因，无法使用 {provider} 的 {model_name} 模型获取完整回应。作为{mbti}类型的专家，我认为{topic}是一个重要话题，需要从多角度深入分析并提出具体解决方案。"
                print(f"使用备用回应: {fallback_response}")
                return fallback_response
                
            # 使用指数退避策略增加重试间隔
            wait_time = retry_delay * (2 ** (retry_count - 1))  # 指数增长的等待时间
            print(f"等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
            
            # 如果是最后一次重试，尝试使用备用模型
            if retry_count == max_retries - 1:
                backup_model = os.getenv("BACKUP_MODEL", "siliconflow:claude-3-opus")
                if backup_model != f"{provider}:{model_name}":
                    print(f"尝试使用备用模型 {backup_model}")
                    backup_provider, backup_model_name = parse_model_string(backup_model)
                    provider = backup_provider
                    model_name = backup_model_name

# 测试API连接
def test_api_connection(provider=None, model=None):
    """测试API连接是否正常"""
    if not provider:
        provider = os.getenv("DEFAULT_PROVIDER", "volcengine")
    if not model:
        model = os.getenv("DEFAULT_MODEL", "").split(":")[-1]
        if not model:
            model = "deepseek-r1-250120"  # 默认模型
    
    print(f"测试 {provider} API 连接，模型: {model}")
    
    # 简单的测试提示
    prompt = "你好，这是一个API连接测试。请回复'连接正常'。"
    
    try:
        response = call_llm_api(provider, model, prompt, max_tokens=20, temperature=0.1)
        if response and not response.startswith("错误") and not response.startswith("API 调用错误"):
            print(f"API连接测试成功: {response}")
            return True, response
        else:
            print(f"API连接测试失败: {response}")
            return False, response
    except Exception as e:
        print(f"API连接测试异常: {str(e)}")
        return False, str(e)

# 开始阶段讨论的函数
def start_phase_discussion(conference_id, phase_id):
    """为会议启动讨论。"""
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

        # 尝试从文件加载现有对话历史
        dialogue_history = []
        history_dir = "dialogue_histories"
        history_file = os.path.join(history_dir, f"dialogue_history_{conference_id}_{phase_id}.json")
        
        try:
            if os.path.exists(history_file):
                with open(history_file, "r", encoding='utf-8') as f:
                    existing_history = json.load(f)
                    if existing_history:
                        print(f"加载了 {len(existing_history)} 条已有对话记录")
                        dialogue_history = existing_history
                        # 如果已有对话记录，直接返回
                        return dialogue_history
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"未找到现有对话历史或文件格式错误，将创建新的对话历史")
        
        # 选择主持人和其他专家
        moderator, other_agents = select_moderator(agents, conference_id)
        if not moderator:
            print("错误：无法选择主持人！")
            return dialogue_history
        
        # 性能优化：限制参与讨论的代理数量
        max_agents_per_round = int(os.getenv("MAX_AGENTS_PER_ROUND", "4"))
        if len(other_agents) > max_agents_per_round - 1:  # 减1是因为已经有一个主持人
            print(f"性能优化：限制每轮讨论的代理数量为 {max_agents_per_round} (总共 {len(agents)} 个代理)")
            # 随机选择指定数量的代理参与讨论
            random.shuffle(other_agents)
            other_agents = other_agents[:max_agents_per_round - 1]
        
        # 统一处理流程：主持人开场 + 专家讨论
        print("第一步：主持人开场...")
        # 主持人搜索信息并开场
        dialogue_history = handle_moderator_opening(moderator, other_agents, topic, conference_id, phase_id)
        
        print("第二步：专家讨论...")
        # 专家讨论
        dialogue_history = handle_expert_discussion(moderator, other_agents, topic, conference_id, phase_id)
        
        print("第三步：添加系统提示...")
        # 添加系统提示，告知用户可以提问
        timestamp = datetime.now().isoformat()
        system_prompt = f"讨论已开始，您可以随时向任何专家提问，或让他们继续讨论。"
        dialogue_history.append({"agent_id": "系统", "speech": system_prompt, "timestamp": timestamp})
        save_dialogue_history(dialogue_history, conference_id, phase_id)
        
        # 如果对话历史为空可能表示出错了
        if not dialogue_history:
            error_msg = "错误：讨论过程未生成有效对话，可能是API调用失败"
            print(error_msg)
            return error_msg
            
        return dialogue_history
    except Exception as e:
        error_msg = f"讨论过程出错: {str(e)}"
        print(error_msg)
        return error_msg

# 处理主持人开场阶段
def handle_moderator_opening(moderator, other_agents, topic, conference_id, phase_id):
    """主持人搜索信息，总结并进行开场发言，然后自动触发专家讨论"""
    dialogue_history = []
    
    # 从环境变量获取是否启用搜索
    enable_search = os.getenv("ENABLE_SEARCH", "true").lower() == "true"
    search_results = None
    
    if enable_search:
        # 从环境变量获取搜索引擎
        search_engine = os.getenv("SEARCH_ENGINE", "searxng")
        print(f"主持人 {moderator.name} 使用 {search_engine} 搜索关于 '{topic}' 的最新信息...")
        search_results = search_latest_info(topic, ", ".join(moderator.background_info.get("skills", [])))
    else:
        search_results = f"搜索功能已禁用。请基于您的专业知识和理解来讨论主题：{topic}"
    
    # 主持人开场发言
    moderator_speech = moderator_opening_speech(moderator, topic, search_results)
    timestamp = datetime.now().isoformat()
    dialogue_history.append({"agent_id": moderator.agent_id, "speech": moderator_speech, "timestamp": timestamp})
    
    # 将对话历史保存到文件，用于实时流式传输
    save_dialogue_history(dialogue_history, conference_id, phase_id)
    print(moderator_speech)
    
    # 自动开始专家讨论
    print(f"主持人开场发言完成，自动开始专家讨论...")
    
    # 进行2轮专家讨论
    discussion_rounds = 2
    print(f"开始 {discussion_rounds} 轮讨论，每轮 {len(other_agents)} 个专家发言")
    
    for round_num in range(discussion_rounds):
        print(f"开始第 {round_num + 1} 轮讨论")
        random.shuffle(other_agents)  # 每轮重新洗牌
        
        for agent in other_agents:
            # 获取上一条发言作为上下文
            previous_speech = dialogue_history[-1] if dialogue_history else None
            
            # 如果previous_speech是用户提问，我们需要确保代理看到提问和回答的上下文
            if previous_speech and previous_speech.get("agent_id") == "用户" and len(dialogue_history) >= 2:
                # 使用倒数第二条记录，也就是代理的回答
                previous_speech = dialogue_history[-2]
            
            # 生成专家发言，传递搜索结果避免重复搜索
            speech = agent_speak(agent.agent_id, conference_id, "专家讨论", topic, previous_speech, search_results)
            timestamp = datetime.now().isoformat()
            dialogue_history.append({"agent_id": agent.agent_id, "speech": speech, "timestamp": timestamp})
            
            # 将对话历史保存到文件，用于实时流式传输
            save_dialogue_history(dialogue_history, conference_id, phase_id)
            print(speech)
    
    # 主持人总结发言
    print(f"主持人 {moderator.name} 准备总结发言...")
    summary_speech = moderator_summary_speech(moderator, topic, dialogue_history)
    timestamp = datetime.now().isoformat()
    dialogue_history.append({"agent_id": moderator.agent_id, "speech": summary_speech, "timestamp": timestamp})
    
    # 将对话历史保存到文件，用于实时流式传输
    save_dialogue_history(dialogue_history, conference_id, phase_id)
    print(summary_speech)
    
    # 添加系统提示，告知用户可以提问
    timestamp = datetime.now().isoformat()
    system_prompt = f"主持人已总结完毕，您现在可以向专家提问。请在下方选择\"提问\"并选择要提问的专家。"
    dialogue_history.append({"agent_id": "系统", "speech": system_prompt, "timestamp": timestamp})
    save_dialogue_history(dialogue_history, conference_id, phase_id)
    
    return dialogue_history

# 处理专家讨论阶段
def handle_expert_discussion(moderator, other_agents, topic, conference_id, phase_id):
    """专家进行2轮讨论，主持人总结"""
    # 尝试加载上一阶段的对话历史
    dialogue_history = []
    prev_history_file = os.path.join("dialogue_histories", f"dialogue_history_{conference_id}_{phase_id-1}.json")
    
    try:
        if os.path.exists(prev_history_file):
            with open(prev_history_file, "r", encoding='utf-8') as f:
                prev_history = json.load(f)
                if prev_history:
                    # 获取主持人的搜索结果和开场白
                    # 注意：我们使用传入的moderator参数，确保使用相同的主持人
                    moderator_opening = next((item for item in prev_history if item.get("agent_id") == moderator.agent_id), None)
                    if moderator_opening:
                        dialogue_history.append(moderator_opening)
    except Exception as e:
        print(f"加载上一阶段对话历史时出错: {str(e)}")
    
    # 如果没有加载到上一阶段的对话历史，则重新生成主持人开场白
    if not dialogue_history:
        # 从环境变量获取是否启用搜索
        enable_search = os.getenv("ENABLE_SEARCH", "true").lower() == "true"
        search_results = None
        
        if enable_search:
            search_engine = os.getenv("SEARCH_ENGINE", "searxng")
            print(f"主持人 {moderator.name} 使用 {search_engine} 搜索关于 '{topic}' 的最新信息...")
            search_results = search_latest_info(topic, ", ".join(moderator.background_info.get("skills", [])))
        else:
            search_results = f"搜索功能已禁用。请基于您的专业知识和理解来讨论主题：{topic}"
        
        # 主持人开场发言
        moderator_speech = moderator_opening_speech(moderator, topic, search_results)
        timestamp = datetime.now().isoformat()
        dialogue_history.append({"agent_id": moderator.agent_id, "speech": moderator_speech, "timestamp": timestamp})
        
        # 将对话历史保存到文件
        save_dialogue_history(dialogue_history, conference_id, phase_id)
        print(moderator_speech)
    
    # 进行2轮专家讨论
    discussion_rounds = 2
    print(f"开始 {discussion_rounds} 轮讨论，每轮 {len(other_agents)} 个专家发言")
    
    for round_num in range(discussion_rounds):
        print(f"开始第 {round_num + 1} 轮讨论")
        random.shuffle(other_agents)  # 每轮重新洗牌
        
        for agent in other_agents:
            # 获取上一条发言作为上下文
            previous_speech = dialogue_history[-1] if dialogue_history else None
            
            # 如果previous_speech是用户提问，我们需要确保代理看到提问和回答的上下文
            if previous_speech and previous_speech.get("agent_id") == "用户" and len(dialogue_history) >= 2:
                # 使用倒数第二条记录，也就是代理的回答
                previous_speech = dialogue_history[-2]
            
            # 生成专家发言，传递搜索结果避免重复搜索
            speech = agent_speak(agent.agent_id, conference_id, "专家讨论", topic, previous_speech, search_results)
            timestamp = datetime.now().isoformat()
            dialogue_history.append({"agent_id": agent.agent_id, "speech": speech, "timestamp": timestamp})
            
            # 将对话历史保存到文件，用于实时流式传输
            save_dialogue_history(dialogue_history, conference_id, phase_id)
            print(speech)
    
    # 主持人总结发言
    print(f"主持人 {moderator.name} 准备总结发言...")
    summary_speech = moderator_summary_speech(moderator, topic, dialogue_history)
    timestamp = datetime.now().isoformat()
    dialogue_history.append({"agent_id": moderator.agent_id, "speech": summary_speech, "timestamp": timestamp})
    
    # 将对话历史保存到文件，用于实时流式传输
    save_dialogue_history(dialogue_history, conference_id, phase_id)
    print(summary_speech)
    
    return dialogue_history

# 初始化用户提问阶段
def initialize_user_question_phase(moderator, other_agents, topic, conference_id, phase_id):
    """初始化用户提问阶段"""
    dialogue_history = []
    
    # 尝试加载上一阶段的对话历史
    prev_history_file = os.path.join("dialogue_histories", f"dialogue_history_{conference_id}_{phase_id-1}.json")
    
    try:
        if os.path.exists(prev_history_file):
            with open(prev_history_file, "r", encoding='utf-8') as f:
                prev_history = json.load(f)
                if prev_history:
                    # 获取主持人的总结发言
                    # 注意：我们使用传入的moderator参数，确保使用相同的主持人
                    moderator_entries = [item for item in prev_history if item.get("agent_id") == moderator.agent_id]
                    if moderator_entries and len(moderator_entries) > 0:
                        # 获取最后一条主持人发言（应该是总结）
                        moderator_summary = moderator_entries[-1]
                        dialogue_history.append(moderator_summary)
    except Exception as e:
        print(f"加载上一阶段对话历史时出错: {str(e)}")
    
    # 如果没有加载到上一阶段的对话历史，则添加一条提示信息
    if not dialogue_history:
        timestamp = datetime.now().isoformat()
        prompt_message = f"现在进入用户提问环节。请向专家提出关于'{topic}'的问题。"
        dialogue_history.append({"agent_id": "系统", "speech": prompt_message, "timestamp": timestamp})
    
    # 将对话历史保存到文件，用于实时流式传输
    save_dialogue_history(dialogue_history, conference_id, phase_id)
    
    return dialogue_history

# 初始化会议结束阶段
def initialize_meeting_end_phase(moderator, other_agents, topic, conference_id, phase_id):
    """初始化会议结束阶段"""
    dialogue_history = []
    
    # 尝试加载上一阶段的对话历史
    prev_history_file = os.path.join("dialogue_histories", f"dialogue_history_{conference_id}_{phase_id-1}.json")
    
    try:
        if os.path.exists(prev_history_file):
            with open(prev_history_file, "r", encoding='utf-8') as f:
                prev_history = json.load(f)
                if prev_history:
                    # 获取最后几条对话记录
                    # 注意：我们确保包含主持人的发言，以保持主持人的一致性
                    last_entries = prev_history[-3:] if len(prev_history) >= 3 else prev_history
                    dialogue_history.extend(last_entries)
                    
                    # 确保主持人信息一致
                    moderator_entry = next((item for item in prev_history if item.get("agent_id") == moderator.agent_id), None)
                    if moderator_entry and not any(item.get("agent_id") == moderator.agent_id for item in dialogue_history):
                        dialogue_history.append(moderator_entry)
    except Exception as e:
        print(f"加载上一阶段对话历史时出错: {str(e)}")
    
    # 添加一条提示信息
    timestamp = datetime.now().isoformat()
    prompt_message = f"会议即将结束。您可以再次提问，发表意见，或选择结束会议。"
    dialogue_history.append({"agent_id": "系统", "speech": prompt_message, "timestamp": timestamp})
    
    # 将对话历史保存到文件，用于实时流式传输
    save_dialogue_history(dialogue_history, conference_id, phase_id)
    
    return dialogue_history

# 代理发言的函数
def agent_speak(agent_id, conference_id, phase_name, topic, previous_speech=None, search_results=None):
    """为阶段生成并返回代理的发言。"""
    agent = get_agent(agent_id)
    if not agent:
        return f"代理 {agent_id} 未找到！"
    
    conference = get_conference(conference_id)
    if not conference:
        return f"未找到ID为 {conference_id} 的会议！"

    return generate_agent_speech(agent, phase_name, topic, previous_speech, search_results)

# 用户干预的函数
def user_intervene(conference_id, phase_id, user_action, target_agent_id=None, user_input=None):
    """允许用户中断或提问。"""
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
        
        # 统一处理用户提问
        print(f"用户向 {agent.name} 提问: {user_input}")
        
        # 使用handle_user_question_phase处理所有用户提问
        return handle_user_question_phase(conference_id, phase_id, agent, provider, model_name, topic, user_input)
    else:
        print(f"无效的用户操作: {user_action}")
        return False

# 处理用户提问阶段的提问
def handle_user_question_phase(conference_id, phase_id, agent, provider, model_name, topic, user_input):
    """处理用户提问阶段的提问，主持人搜索不同信源，其他专家讨论1轮，然后主持人总结"""
    # 获取会议参与者
    conference = get_conference(conference_id)
    agents = [get_agent(agent_id) for agent_id in conference.participant_agent_ids]
    
    # 使用相同的随机种子选择主持人，确保与第一阶段相同
    moderator, other_agents = select_moderator(agents, conference_id)
    
    # 主持人搜索不同信源
    print(f"主持人 {moderator.name} 搜索关于用户问题的不同信源...")
    # 注意：search_latest_info 只接受两个参数，移除第三个参数 search_engine
    search_info = search_latest_info(f"{topic} {user_input}", ", ".join(agent.background_info.get("skills", [])))
    
    # 加载当前对话历史
    dialogue_history = []
    history_dir = "dialogue_histories"
    history_file = os.path.join(history_dir, f"dialogue_history_{conference_id}_{phase_id}.json")
    
    try:
        if os.path.exists(history_file):
            with open(history_file, "r", encoding='utf-8') as f:
                dialogue_history = json.load(f)
    except Exception as e:
        print(f"加载对话历史时出错: {str(e)}")
    
    # 添加用户提问
    timestamp = datetime.now().isoformat()
    user_question = f"提问给 {agent.name}: {user_input}"
    dialogue_history.append({"agent_id": "用户", "speech": user_question, "timestamp": timestamp})
    
    # 保存对话历史
    save_dialogue_history(dialogue_history, conference_id, phase_id)
    
    # 生成专家回答
    prompt = f"""作为 {agent.name}，请回答用户关于 {topic} 的问题："{user_input}"

以下是主持人搜索到的关于该问题的最新信息，请在回答中适当参考：
{search_info}

你的回答需要：
1. 直接切入问题核心，避免不必要的铺垫
2. 基于你的 {', '.join(agent.background_info.get('skills', []))} 专业背景，提供具体且全面的分析
3. 引用相关研究、数据或案例支持你的观点
4. 如可能，提出1个具体且可行的解决方案或建议
5. 简要讨论可能的挑战或限制

请以 {agent.communication_style.get('tone', '中立')} 的语调回答，保持专业性的同时确保内容通俗易懂。
请用中文回答，引用其他代理时请使用他们的名字而不是代号。
限制在200字以内，保持内容简洁但有深度。"""
    
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
        
        # 添加专家回答到对话历史
        timestamp = datetime.now().isoformat()
        dialogue_history.append({"agent_id": agent.agent_id, "speech": answer, "timestamp": timestamp})
        
        # 保存对话历史
        save_dialogue_history(dialogue_history, conference_id, phase_id)
        print(f"专家 {agent.name} 已回答用户问题")
        
        # 其他专家讨论1轮
        # 限制参与讨论的专家数量
        max_agents_per_round = int(os.getenv("MAX_AGENTS_PER_ROUND", "2"))  # 减少专家数量以提高性能
        if len(other_agents) > max_agents_per_round:
            random.shuffle(other_agents)
            other_agents = other_agents[:max_agents_per_round]
        
        # 排除已回答问题的专家
        other_agents = [a for a in other_agents if a.agent_id != agent.agent_id]
        
        # 如果还有其他专家，让他们进行讨论
        if other_agents:
            print(f"其他专家开始讨论用户的问题... (共 {len(other_agents)} 位专家)")
            for i, other_agent in enumerate(other_agents):
                print(f"专家 {i+1}/{len(other_agents)}: {other_agent.name} 正在准备发言...")
                
                # 获取用户问题和专家回答作为上下文
                user_question_entry = dialogue_history[-2] if len(dialogue_history) >= 2 else None
                expert_answer_entry = dialogue_history[-1] if dialogue_history else None
                
                # 为其他专家创建特定的提示，确保他们参考用户问题和专家回答
                expert_prompt = f"""作为 {other_agent.name}，请针对以下用户问题和专家回答发表您的看法：

用户问题: {user_input}

{agent.name} 的回答:
{answer}

以下是关于该问题的最新信息，请在回答中适当参考：
{search_info}

请基于您的 {', '.join(other_agent.background_info.get('skills', []))} 专业背景，对 {agent.name} 的回答进行补充、扩展或提供不同角度的见解。
您可以：
1. 补充遗漏的重要信息
2. 提供不同的专业视角
3. 友善地指出可能的不准确之处
4. 分享相关的案例或研究

请以 {other_agent.communication_style.get('tone', '中立')} 的语调回答，保持专业性的同时确保内容通俗易懂。
请用中文回答，引用其他专家时请使用他们的名字而不是代号。
限制在200字以内，保持内容简洁但有深度。"""

                # 使用与主要专家相同的提供商和模型
                print(f"正在使用 {provider} 的 {model_name} 模型生成 {other_agent.name} 的回应...")
                try:
                    speech = call_llm_api(
                        provider, 
                        model_name, 
                        expert_prompt, 
                        max_tokens=int(os.getenv("MAX_TOKENS", "4000")),
                        temperature=float(os.getenv("TEMPERATURE", "0.7"))
                    )
                    
                    # 检查返回的结果是否包含错误信息
                    if speech.startswith("错误：") or speech.startswith("API 调用错误："):
                        raise Exception(speech)
                        
                    # 替换代理ID为对应名称
                    speech = get_referenced_agent_name(speech, conference_agents)
                except Exception as e:
                    speech = f"很抱歉，由于技术原因，{other_agent.name} 暂时无法参与讨论。({str(e)})"
                
                timestamp = datetime.now().isoformat()
                dialogue_history.append({"agent_id": other_agent.agent_id, "speech": speech, "timestamp": timestamp})
                
                # 保存对话历史
                save_dialogue_history(dialogue_history, conference_id, phase_id)
                print(f"专家 {other_agent.name} 已完成发言")
        else:
            print("没有其他专家可以参与讨论")
        
        # 主持人总结讨论
        print(f"主持人 {moderator.name} 准备总结讨论...")
        summary_speech = moderator_summary_speech(moderator, topic, dialogue_history)
        timestamp = datetime.now().isoformat()
        dialogue_history.append({"agent_id": moderator.agent_id, "speech": summary_speech, "timestamp": timestamp})
        
        # 保存对话历史
        save_dialogue_history(dialogue_history, conference_id, phase_id)
        print(f"主持人 {moderator.name} 已完成总结")
        
        # 添加系统提示，告知用户可以继续提问或结束会议
        timestamp = datetime.now().isoformat()
        system_prompt = f"主持人已总结完毕，您可以继续向专家提问，或选择结束会议。"
        dialogue_history.append({"agent_id": "系统", "speech": system_prompt, "timestamp": timestamp})
        save_dialogue_history(dialogue_history, conference_id, phase_id)
        print("系统提示已添加，用户可以继续提问或结束会议")
        
    except Exception as e:
        print(f"处理用户提问时出错: {str(e)}")
        answer = f"错误：无法生成回应 ({str(e)})"
        
    return answer

def save_dialogue_history(dialogue_history, conference_id, phase_id):
    """保存对话历史到JSON文件"""
    # 确保dialogue_histories目录存在
    history_dir = "dialogue_histories"
    if not os.path.exists(history_dir):
        os.makedirs(history_dir)
        print(f"创建对话历史目录: {history_dir}")
        
    # 构建文件名
    filename = f"dialogue_history_{conference_id}_{phase_id}.json"
    file_path = os.path.join(history_dir, filename)
    
    # 保存对话历史
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dialogue_history, f, ensure_ascii=False, indent=2)
        print(f"对话历史已保存到 {file_path} (共 {len(dialogue_history)} 条记录)")
    except Exception as e:
        print(f"保存对话历史时出错: {str(e)}")
    
    return filename

# 选择主持人的函数
def select_moderator(agents, conference_id=None, phase_id=None):
    """
    从参与会议的专家中选择一位作为主持人
    
    参数:
        agents: 参与会议的专家列表
        conference_id: 会议ID，用于保持主持人选择的一致性
        phase_id: 阶段ID，不再使用，保留参数是为了兼容性
        
    返回:
        选定的主持人和剩余的专家列表
    """
    if not agents or len(agents) == 0:
        return None, []
    
    # 如果只有一位专家，那么他就是主持人
    if len(agents) == 1:
        return agents[0], []
    
    # 只使用会议ID作为随机种子，忽略阶段ID，确保整个会议只有一个主持人
    if conference_id:
        # 使用会议ID作为随机种子
        seed = hash(f"{conference_id}") % 10000
        random.seed(seed)
        
    # 随机选择一位专家作为主持人
    moderator_index = random.randint(0, len(agents) - 1)
    moderator = agents[moderator_index]
    
    # 创建剩余专家列表
    remaining_agents = agents.copy()
    remaining_agents.pop(moderator_index)
    
    # 重置随机种子
    random.seed()
    
    print(f"已选择 {moderator.name} 作为本次讨论的主持人")
    return moderator, remaining_agents

# 主持人开场发言函数
def moderator_opening_speech(moderator, topic, search_results=None):
    """
    生成主持人的开场白，包括主题介绍和搜索结果
    
    参数:
        moderator: 主持人对象
        topic: 讨论主题
        search_results: 搜索结果，如果为None则会进行搜索
        
    返回:
        主持人的开场白
    """
    skills = ", ".join(moderator.background_info.get("skills", []))
    mbti = moderator.personality_traits.get("mbti", "未知")
    style = moderator.communication_style.get("style", "中立")
    tone = moderator.communication_style.get("tone", "中立")
    
    # 如果没有提供搜索结果，则进行搜索
    if search_results is None:
        # 从环境变量获取是否启用搜索
        enable_search = os.getenv("ENABLE_SEARCH", "true").lower() == "true"
        
        if enable_search:
            # 从环境变量获取搜索引擎
            search_engine = os.getenv("SEARCH_ENGINE", "tavily")
            print(f"主持人 {moderator.name} 使用 {search_engine} 搜索关于 '{topic}' 的最新信息...")
            search_results = search_latest_info(topic, skills)
        else:
            search_results = f"搜索功能已禁用。请基于您的专业知识和理解来讨论主题：{topic}"
    
    print(f"主持人 {moderator.name} 搜索到的最新信息: {search_results[:100]}..." if len(search_results) > 100 else search_results)
    
    # 构建主持人开场白的提示词
    prompt = f"""作为 {moderator.name}，你是{moderator.background_info["field"]}领域的顶尖专家，同时也是本次关于"{topic}"讨论的主持人。

你的MBTI类型是{mbti}，沟通风格是{style}，语气{tone}。
你的专业技能包括: {skills}

以下是关于该主题的最新信息，请在开场白中适当参考：
{search_results}

作为主持人，请提供一个简洁、专业且引人入胜的开场白，包括：

1. 简短介绍本次讨论的主题"{topic}"及其重要性
2. 概述该主题的1-2个关键方面或挑战
3. 分享1个来自最新研究或数据的重要发现
4. 提出1-2个值得深入探讨的关键问题
5. 邀请其他专家从各自专业角度参与讨论

回复格式要求:
1. 不要使用Markdown格式
2. 不要包含标题
3. 以"各位专家，欢迎参加今天关于'{topic}'的圆桌讨论..."开头
4. 以"请各位专家从自己的专业角度分享见解..."结尾
5. 回应长度必须控制在200字以内
6. 必须使用中文回答
7. 语言必须简洁、精确且富有洞察力
"""

    # 获取该代理的模型字符串
    agent_model = os.getenv(f"MODEL_{moderator.agent_id}", os.getenv("DEFAULT_MODEL", f"{DEFAULT_PROVIDER}:gpt-3.5-turbo"))
    
    # 解析模型字符串，获取提供商和模型名称
    provider, model_name = parse_model_string(agent_model)
    
    # 调用 API
    print(f"正在使用 {provider} 的 {model_name} 模型生成 {moderator.name} 的主持人开场白...")
    speech = call_llm_api(
        provider, 
        model_name, 
        prompt, 
        max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
        temperature=float(os.getenv("TEMPERATURE", "0.7"))
    )
    
    # 检查返回的结果是否包含错误信息
    if speech and not speech.startswith("错误：") and not speech.startswith("API 调用错误："):
        return speech
    else:
        # 如果API调用失败，返回一个基本的开场白
        return f"""各位专家，欢迎参加今天关于'{topic}'的圆桌讨论。

很遗憾，在准备开场白时遇到了技术问题。但这不影响我们今天的讨论。

请各位专家从自己的专业角度分享对'{topic}'的见解和建议。

{speech if speech else "API调用失败，无法生成完整开场白。"}
"""

# 主持人总结发言函数
def moderator_summary_speech(moderator, topic, dialogue_history):
    """
    生成主持人的总结发言，基于之前的对话
    
    参数:
        moderator: 主持人对象
        topic: 讨论主题
        dialogue_history: 之前的对话历史
        
    返回:
        主持人的总结发言
    """
    if not dialogue_history or len(dialogue_history) == 0:
        return f"由于没有有效的对话历史，{moderator.name}无法提供总结。"
    
    skills = ", ".join(moderator.background_info.get("skills", []))
    mbti = moderator.personality_traits.get("mbti", "未知")
    style = moderator.communication_style.get("style", "中立")
    tone = moderator.communication_style.get("tone", "中立")
    
    # 提取对话内容
    dialogue_content = ""
    for entry in dialogue_history:
        agent_id = entry.get("agent_id", "未知")
        if agent_id != moderator.agent_id:  # 排除主持人自己的发言
            agent_name = get_agent_name_by_id(agent_id) or agent_id
            speech = entry.get("speech", "")
            dialogue_content += f"{agent_name}: {speech}\n\n"
    
    # 构建主持人总结发言的提示词
    prompt = f"""作为 {moderator.name}，你是{moderator.background_info["field"]}领域的顶尖专家，同时也是本次关于"{topic}"讨论的主持人。

你的MBTI类型是{mbti}，沟通风格是{style}，语气{tone}。
你的专业技能包括: {skills}

以下是专家们关于"{topic}"的讨论内容：
{dialogue_content}

作为主持人，请提供一个简洁、专业且有洞察力的讨论总结，包括：

1. 简短回顾本次讨论的主题"{topic}"
2. 总结各位专家提出的2-3个主要观点和见解
3. 指出1个专家们达成共识的方面
4. 分析1个存在分歧或需要进一步探讨的问题
5. 提炼出1-2个关键的行动建议或结论

回复格式要求:
1. 不要使用Markdown格式
2. 不要包含标题
3. 以"感谢各位专家的精彩分享..."开头
4. 以"下面，我们欢迎听众提问，请各位专家继续为大家解答疑惑..."结尾
5. 回应长度必须控制在200字以内
6. 必须使用中文回答
7. 语言必须简洁、精确且富有洞察力
"""

    # 获取该代理的模型字符串
    agent_model = os.getenv(f"MODEL_{moderator.agent_id}", os.getenv("DEFAULT_MODEL", f"{DEFAULT_PROVIDER}:gpt-3.5-turbo"))
    
    # 解析模型字符串，获取提供商和模型名称
    provider, model_name = parse_model_string(agent_model)
    
    # 调用 API
    print(f"正在使用 {provider} 的 {model_name} 模型生成 {moderator.name} 的总结发言...")
    speech = call_llm_api(
        provider, 
        model_name, 
        prompt, 
        max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
        temperature=float(os.getenv("TEMPERATURE", "0.7"))
    )
    
    # 检查返回的结果是否包含错误信息
    if speech and not speech.startswith("错误：") and not speech.startswith("API 调用错误："):
        return speech
    else:
        # 如果API调用失败，返回一个基本的总结
        return f"""感谢各位专家关于"{topic}"的精彩分享。

很遗憾，在准备总结发言时遇到了技术问题。但这不影响我们今天讨论的价值。

下面，我们欢迎听众提问，请各位专家继续为大家解答疑惑。

{speech if speech else "API调用失败，无法生成完整总结。"}
"""

# 测试代码
if __name__ == "__main__":
    conference_id = "C001"
    print("=== 主题讨论阶段 ===")
    start_phase_discussion(conference_id, 0)
    user_intervene(conference_id, 0, "question", "A004", "AI伦理如何影响沟通？")
    user_intervene(conference_id, 0, "interrupt")
    print("\n=== 专家分享阶段 ===")
    start_phase_discussion(conference_id, 1)