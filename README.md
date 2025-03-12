# RoundTable对话系统

一个基于多代理的智能对话和会议系统，支持多种LLM API提供商。

## 项目简介

RoundTable是一个创新的多代理对话系统，它模拟了一个由多位AI专家参与的圆桌会议。系统支持多种大语言模型(LLM)提供商，包括OpenAI、Anthropic、Google Gemini等，通过统一的接口进行调用。

### 核心功能

- **多专家协作**：多个AI代理以不同专业背景和性格特点参与讨论
- **实时搜索集成**：支持Tavily搜索引擎，为专家提供最新信息
- **灵活的会议流程**：支持主题讨论和用户提问等多种互动方式
- **多模型支持**：兼容多种LLM提供商，可根据需要灵活配置

## 最新更新

### 2025年3月更新

- **专家回答优化**：所有专家回答现在限制在200字以内，同时保持深度和洞察力
- **引用要求**：专家回答现在需要引用研究数据、行业案例或专业经验
- **解决方案改进**：专家提出的解决方案现在包含具体实施步骤和预期效果
- **默认搜索引擎**：将默认搜索引擎从SearXNG更改为Tavily，提高搜索稳定性
- **UI简化**：移除了"推进阶段"按钮，简化会议流程

## 安装指南

### 环境要求

- Python 3.8+
- 支持Windows、macOS和Linux

### 安装步骤

1. 克隆仓库
   ```bash
   git clone https://github.com/maxwell66666/RoundTable-AI-Conference.git
   cd RoundTable-AI-Conference
   ```

2. 创建并激活虚拟环境
   ```bash
   # 在Windows上
   python -m venv venv
   venv\Scripts\activate

   # 在Linux/macOS上
   python3 -m venv venv
   source venv/bin/activate
   ```

3. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

4. 配置环境变量
   ```bash
   # 复制示例配置
   cp .env.example .env
   
   # 编辑.env文件，填入你的API密钥
   ```

5. 启动应用
   ```bash
   uvicorn app:app --reload
   ```

6. 访问应用
   在浏览器中打开 http://localhost:8000

## 使用指南

### 创建会议

1. 在主页点击"创建新会议"
2. 填写会议标题、描述和主题
3. 选择参与会议的专家（建议选择3-5位不同领域的专家）
4. 点击"创建会议"按钮

### 会议流程

1. **开始会议**：点击"开始会议"按钮，主持人会介绍主题并邀请专家发言
2. **专家讨论**：专家们会轮流发表观点，并对其他专家的观点进行回应
3. **用户提问**：您可以在提问框中输入问题，并选择要回答问题的专家
4. **结束会议**：讨论结束后，点击"结束会议"按钮

### API调用

RoundTable提供了RESTful API，可以通过编程方式创建和管理会议。

#### 创建会议

```bash
curl -X POST "http://localhost:8000/api/conferences" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "AI伦理讨论",
    "description": "探讨AI发展中的伦理问题",
    "topic": "人工智能伦理",
    "participant_agent_ids": ["A001", "A002", "A003", "A004"]
  }'
```

#### 获取会议列表

```bash
curl -X GET "http://localhost:8000/api/conferences"
```

#### 开始会议

```bash
curl -X POST "http://localhost:8000/api/conferences/{conference_id}/start"
```

#### 提交用户问题

```bash
curl -X POST "http://localhost:8000/api/conferences/{conference_id}/question" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "AI如何影响就业市场?",
    "expert_id": "A002"
  }'
```

#### 结束会议

```bash
curl -X POST "http://localhost:8000/api/conferences/{conference_id}/end"
```

## 配置说明

### LLM提供商配置

RoundTable支持多种LLM提供商，您可以在`.env`文件中配置：

```
# 默认使用的API提供商
DEFAULT_PROVIDER=oneapi

# OneAPI配置（统一接口）
ONEAPI_API_KEY=your_oneapi_key_here
ONEAPI_BASE_URL=https://api.ffa.chat/v1

# OpenAI配置
OPENAI_API_KEY=your_openai_key_here

# Anthropic配置
ANTHROPIC_API_KEY=your_anthropic_key_here

# 其他提供商...
```

### 搜索引擎配置

```
# 搜索引擎设置
ENABLE_SEARCH=true
SEARCH_ENGINE=tavily
TAVILY_API_KEY=your_tavily_api_key_here
```

### 专家模型配置

您可以为每个专家配置不同的模型：

```
MODEL_A001=oneapi:gpt-4
MODEL_A002=anthropic:claude-3-sonnet
MODEL_A003=gemini:gemini-pro
# 其他专家...
```

## 故障排除

### 常见问题

1. **API连接错误**
   - 检查API密钥是否正确
   - 确认网络连接是否稳定
   - 验证API提供商服务是否可用

2. **搜索功能不工作**
   - 确认已设置正确的Tavily API密钥
   - 检查`ENABLE_SEARCH`是否设为`true`

3. **专家回答质量问题**
   - 尝试使用更高级的模型（如GPT-4或Claude-3）
   - 调整`TEMPERATURE`参数（默认为0.7）

### 获取帮助

如有问题，请在GitHub仓库提交Issue或联系项目维护者。 