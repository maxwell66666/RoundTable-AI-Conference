# 多 LLM 提供商配置说明

本项目已更新为支持多种 LLM 提供商 API，让您可以灵活选择和组合不同的模型来实现代理对话。

## 1. 概述

系统支持以下 LLM 提供商：

- **OneAPI** - 统一 API 网关，支持多种模型
- **OpenAI** - GPT 系列模型
- **Anthropic** - Claude 系列模型
- **Google** - Gemini 系列模型
- **DeepSeek** - DeepSeek 系列模型
- **SiliconFlow** - 多模型支持
- **火山引擎** - 字节跳动的 AI 平台
- **腾讯云** - 混元大模型
- **阿里云** - 通义千问等模型

## 2. 配置格式

在 `.env` 文件中，配置采用以下格式：

```
# API 提供商配置
# ====================

# 默认使用的 API 提供商
DEFAULT_PROVIDER=oneapi

# OneAPI 配置
ONEAPI_API_KEY=your_oneapi_key_here
ONEAPI_BASE_URL=https://api.ffa.chat/v1

# OpenAI 配置
OPENAI_API_KEY=your_openai_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# 其他提供商配置...

# 模型配置
# ====================

# 代理模型映射 - 格式：provider:model_name
MODEL_A001=oneapi:gpt-4
MODEL_A002=anthropic:claude-3-sonnet
MODEL_A003=gemini:gemini-pro
MODEL_A004=deepseek:deepseek-chat
MODEL_A005=siliconflow:claude-3-opus
MODEL_A006=volcengine:moonshot-v1
MODEL_A007=tencentcloud:hunyuan
MODEL_A008=aliyun:qwen-turbo

# 默认模型
DEFAULT_MODEL=oneapi:gpt-3.5-turbo

# 模型参数
MAX_TOKENS=4096
TEMPERATURE=0.7
```

## 3. 模型指定格式

为每个代理指定模型时，使用 `provider:model_name` 格式：

- `oneapi:gpt-4o` - 使用 OneAPI 的 GPT-4o 模型
- `anthropic:claude-3-sonnet` - 使用 Anthropic 的 Claude 3 Sonnet 模型
- `gemini:gemini-pro` - 使用 Google 的 Gemini Pro 模型

## 4. 多代理多模型组合

您可以为不同代理分配不同提供商的模型：

```
MODEL_A001=oneapi:gpt-4o
MODEL_A002=anthropic:claude-3-sonnet
MODEL_A003=gemini:gemini-pro
MODEL_A004=openai:gpt-4-turbo
MODEL_A005=deepseek:deepseek-chat
```

这样，每个代理都会使用指定的提供商和模型生成回应，创建多样化的对话体验。

## 5. 安装依赖

使用某些提供商可能需要安装额外的依赖。`requirements.txt` 文件中包含了所有可能需要的依赖，您可以根据需要启用它们：

```bash
# 基本安装
pip install -r requirements.txt

# 安装特定提供商的依赖
pip install anthropic  # Anthropic API
pip install google-generativeai  # Google Gemini API
pip install tencentcloud-sdk-python tencentcloud-sdk-python-hunyuan  # 腾讯云 API
pip install aliyun-python-sdk-core  # 阿里云 API
```

## 6. 故障排除

如果遇到 API 调用问题：

1. 检查对应提供商的 API 密钥和 URL 是否正确配置
2. 确认您指定的模型在该提供商中可用
3. 检查相关 SDK 是否已安装
4. 查看日志中的错误信息以确定具体问题
5. 尝试将 `MAX_RETRIES` 环境变量设置为更高的值

## 7. 模型参数调整

您可以在 `.env` 文件中调整全局模型参数：

```
MAX_TOKENS=4096     # 生成的最大 token 数
TEMPERATURE=0.7     # 创造性/多样性参数
MAX_RETRIES=3       # API 调用失败时的最大重试次数
```

## 8. 添加新的提供商

如需添加新的 LLM 提供商，需要修改 `round_table.py` 文件：

1. 在 `SUPPORTED_PROVIDERS` 列表中添加新提供商
2. 在 `init_api_client` 函数中添加新提供商的初始化逻辑
3. 如需特殊的 API 调用逻辑，在 `call_llm_api` 函数中添加处理代码 