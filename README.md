# RoundTable对话系统

一个基于多代理的智能对话和会议系统，支持多种LLM API提供商。

![GitHub release (latest by date)](https://img.shields.io/github/v/release/yourusername/RoundTable)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/yourusername/RoundTable/持续集成与部署)
![GitHub stars](https://img.shields.io/github/stars/yourusername/RoundTable)
![License](https://img.shields.io/github/license/yourusername/RoundTable)

## 最新更新

### 2024年3月更新

- **专家回答优化**：所有专家回答现在限制在200字以内，同时保持深度和洞察力
- **引用要求**：专家回答现在需要引用研究数据、行业案例或专业经验
- **解决方案改进**：专家提出的解决方案现在包含具体实施步骤和预期效果
- **默认搜索引擎**：将默认搜索引擎从SearXNG更改为Tavily，提高搜索稳定性
- **UI简化**：移除了"推进阶段"按钮，简化会议流程

## 版本管理

该项目使用语义化版本控制：`主版本号.次版本号.修订号`

- **主版本号**：不兼容的API变更
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

当前版本: **1.2.0**

## 开发环境设置

1. 克隆仓库
   ```bash
   git clone <repository-url>
   cd RoundTable
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

5. 运行数据库迁移
   ```bash
   python db_migrations.py
   ```

6. 启动应用
   ```bash
   uvicorn app:app --reload
   ```

## 版本管理命令

项目提供了一个版本管理工具`release.py`，用于版本号更新、数据库迁移和创建发布包。

### 更新版本号

```bash
# 更新修订号 (1.0.0 -> 1.0.1)
python release.py bump --type patch

# 更新次版本号 (1.0.0 -> 1.1.0)
python release.py bump --type minor

# 更新主版本号 (1.0.0 -> 2.0.0)
python release.py bump --type major

# 设置特定版本号
python release.py bump --version 1.2.3

# 自动生成变更日志(基于git提交)
python release.py bump --auto-changelog
```

### 运行数据库迁移

```bash
python release.py migrate
```

### 创建发布包

```bash
# 创建发布包（会更新补丁版本号，运行迁移脚本，并创建归档文件）
python release.py release

# 指定版本类型
python release.py release --type minor

# 指定具体版本号
python release.py release --version 1.2.3

# 自动生成变更日志
python release.py release --auto-changelog

# 跳过备份步骤
python release.py release --skip-backup
```

## GitHub集成

RoundTable项目支持与GitHub深度集成，提供完整的代码管理、版本控制和CI/CD流程。

### GitHub发布

使用自定义GitHub发布脚本创建版本发布：

```bash
# 使用当前版本创建发布
python release_github.py --token YOUR_GITHUB_TOKEN

# 创建预发布版本
python release_github.py --token YOUR_GITHUB_TOKEN --prerelease

# 创建草稿发布
python release_github.py --token YOUR_GITHUB_TOKEN --draft
```

### GitHub Actions

项目包含两个主要的GitHub Actions工作流：

1. **持续集成与部署** (`.github/workflows/ci-cd.yml`)
   - 自动运行测试
   - 构建和推送Docker镜像
   - 自动更新版本号

2. **自动备份** (`.github/workflows/backup.yml`)
   - 定期创建系统备份
   - 可手动触发备份流程

### GitHub工作流程

详细的GitHub工作流程文档位于 [docs/github_workflow.md](docs/github_workflow.md)，包含：

- 分支管理策略
- 提交信息规范
- 发布流程
- 安全实践

## 备份与恢复

项目提供了强大的备份系统，支持本地备份和云存储备份。

### 配置备份

首次运行备份命令时会自动创建默认配置文件 `backup_config.ini`。你可以编辑该文件以配置备份选项，包括:
- 备份保留时间
- 是否包含对话历史
- 云存储提供商配置(AWS S3, Google Cloud Storage, Azure Blob Storage)

```bash
# 查看备份配置
python backup.py config
```

### 手动备份

```bash
# 创建备份(本地+已启用的云存储)
python backup.py create

# 仅创建本地备份(不上传到云存储)
python backup.py create --no-upload
```

### 查看备份列表

```bash
# 查看本地备份
python backup.py list-local

# 查看云存储备份
python backup.py list-cloud --provider aws
python backup.py list-cloud --provider gcp
python backup.py list-cloud --provider azure
```

### 从备份恢复

```bash
# 从本地备份恢复
python backup.py restore backups/roundtable_v1.1.0_20240620_120000.tar.gz

# 从云存储下载备份
python backup.py download --provider aws roundtable_v1.1.0_20240620_120000.tar.gz

# 从云存储下载并恢复
python backup.py download --provider aws roundtable_v1.1.0_20240620_120000.tar.gz
python backup.py restore backups/roundtable_v1.1.0_20240620_120000.tar.gz
```

### 自动备份

系统支持多种自动备份方式：

1. **使用系统调度**
   ```bash
   # 创建自动备份脚本
   python backup.py schedule
   ```

2. **使用GitHub Actions**
   - 配置GitHub Actions工作流程进行定期备份
   - 在代码仓库的Actions选项卡中查看备份日志

#### Windows系统
创建的脚本为 `schedule_backup.bat`，你可以使用Windows任务计划程序设置定时任务。

#### Linux/Mac系统
创建的脚本为 `schedule_backup.sh`，你可以使用crontab设置定时任务:

```bash
# 编辑crontab
crontab -e

# 添加以下行以设置每天凌晨2点运行备份（替换路径）
0 2 * * * cd /path/to/roundtable && ./schedule_backup.sh
```

## 云存储集成

要使用云存储功能，需要安装相应的依赖并配置凭证。

### AWS S3

1. 在requirements.txt中取消注释boto3依赖，然后运行 `pip install -r requirements.txt`
2. 在`backup_config.ini`中配置AWS区域、存储桶和凭证

### Google Cloud Storage

1. 在requirements.txt中取消注释google-cloud-storage依赖，然后运行 `pip install -r requirements.txt`
2. 下载服务账号凭证JSON文件，并在`backup_config.ini`中配置路径

### Azure Blob Storage

1. 在requirements.txt中取消注释azure-storage-blob依赖，然后运行 `pip install -r requirements.txt`
2. 在`backup_config.ini`中配置连接字符串和容器信息

## Docker部署

项目提供了Docker支持，可以使用Docker容器进行部署。

### 使用Docker Compose部署

1. 确保已安装Docker和Docker Compose

2. 配置环境变量
   ```bash
   cp .env.example .env
   # 编辑.env文件，填入你的API密钥
   ```

3. 构建并启动容器
   ```bash
   docker-compose up -d
   ```

4. 查看应用日志
   ```bash
   docker-compose logs -f
   ```

5. 停止应用
   ```bash
   docker-compose down
   ```

### 手动构建Docker镜像

```bash
# 构建镜像
docker build -t roundtable:1.2.0 .

# 运行容器
docker run -d -p 8000:8000 --name roundtable -v $(pwd)/data:/app/data -v $(pwd)/.env:/app/.env:ro roundtable:1.2.0
```

### Docker中使用备份功能

在Docker环境中，建议将备份目录挂载为数据卷，以确保备份文件不会随容器删除而丢失:

```bash
# 在docker-compose.yml中添加以下卷挂载
volumes:
  - ./data:/app/data
  - ./backups:/app/backups
  - ./.env:/app/.env:ro
```

然后在容器内执行备份:

```bash
docker exec roundtable-app python backup.py create
```

## 数据库结构

系统使用SQLite数据库，包含以下主要表：

- `agents`：存储代理信息
- `conferences`：存储会议信息
- `conversations`：存储对话历史
- `response_ratings`：存储回答评分（从版本1.1开始）
- `users`：存储用户信息（从版本1.1开始）
- `db_migrations`：存储数据库迁移记录

## 系统架构

系统由以下主要组件组成：

- `app.py`：FastAPI应用主入口
- `round_table.py`：对话管理核心逻辑
- `conference_organizer.py`：会议管理逻辑
- `agent_db.py`：代理数据管理
- `version.py`：版本信息管理
- `db_migrations.py`：数据库迁移工具
- `backup.py`：备份与恢复系统
- `release.py`：版本发布工具
- `release_github.py`：GitHub发布工具

## 贡献指南

1. Fork项目
2. 创建新分支 (`git checkout -b feature/amazing-feature`)
3. 提交你的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

[MIT License](LICENSE)

# OpenRouter API 支持

RoundTable 现在支持使用 OpenRouter API 作为模型提供商，这为您提供了更多的模型选择和更稳定的 API 访问。

## 配置 OpenRouter

1. 注册 OpenRouter 账户并获取 API 密钥：
   - 访问 [OpenRouter](https://openrouter.ai/) 并创建账户
   - 在控制面板中生成 API 密钥

2. 在 `.env` 文件中添加以下配置：
   ```
   OPENROUTER_API_KEY=your_openrouter_key_here
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   ```

3. 使用 OpenRouter 模型：
   - 在创建会议时，指定模型为 `openrouter:模型名称`
   - 例如：`openrouter:anthropic/claude-3-opus:20240229`

## 可用模型

OpenRouter 提供了多种模型，包括：

- `anthropic/claude-3-opus:20240229`
- `anthropic/claude-3-sonnet:20240229`
- `anthropic/claude-3-haiku:20240307`
- `openai/gpt-4-turbo`
- `openai/gpt-4o`
- `google/gemini-pro`
- `meta-llama/llama-3-70b-instruct`

完整的模型列表请参考 [OpenRouter 模型列表](https://openrouter.ai/docs#models)。

## 优势

- **API 稳定性**：OpenRouter 提供了多个后端服务，提高了 API 的可用性和稳定性
- **模型多样性**：可以访问多个提供商的模型，而只需要一个 API 密钥
- **简化计费**：统一的计费系统，无需管理多个 API 提供商的账单

## 故障排除

如果遇到 OpenRouter API 连接问题：

1. 确认 API 密钥是否正确
2. 检查网络连接是否稳定
3. 验证模型名称是否正确
4. 尝试增加 `API_TIMEOUT` 值（默认为 30 秒） 