# 贡献指南

感谢您对 RoundTable 项目的关注！我们欢迎各种形式的贡献，包括错误报告、功能请求、文档改进和代码贡献。

## 报告问题

如果您发现了 bug 或有新功能建议，请通过 Issues 页面提交，并包含以下信息：

- 详细的问题描述或功能请求
- 问题的复现步骤（如适用）
- 您的操作系统和 Python 版本
- 相关的配置信息（需移除敏感数据）

## 开发环境设置

1. Fork 这个仓库
2. 克隆您的 fork:
   ```bash
   git clone https://github.com/your-username/roundtable.git
   cd roundtable
   ```
3. 创建新的分支:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. 安装开发依赖:
   ```bash
   pip install -r requirements.txt
   ```
5. 配置开发环境:
   ```bash
   cp .env.example .env.dev
   # 编辑 .env.dev 文件，填写必要的 API 密钥和配置
   ```

## 代码贡献指南

### 代码风格

我们使用以下工具来保持代码质量：

- **Black**: 用于代码格式化
- **Flake8**: 用于代码质量检查
- **MyPy**: 用于类型检查

提交前请运行：
```bash
black .
flake8 .
mypy .
```

### 提交消息规范

请遵循以下提交消息格式：

```
类型(范围): 简短描述

详细描述（如有必要）
```

类型包括：
- **feat**: 新功能
- **fix**: 错误修复
- **docs**: 文档更改
- **style**: 不影响代码含义的格式变更
- **refactor**: 重构代码
- **test**: 添加或修改测试
- **chore**: 构建过程或辅助工具变动

### 提交贡献

1. 确保代码通过所有测试和质量检查
2. 将您的更改提交到您的分支:
   ```bash
   git commit -m "feat: 添加了新功能"
   git push origin feature/your-feature-name
   ```
3. 创建一个 Pull Request 到主仓库

## 添加新 API 提供商

如需添加新的 LLM API 提供商，请遵循以下步骤：

1. 在 `round_table.py` 中的 `SUPPORTED_PROVIDERS` 列表中添加新提供商名称
2. 在 `init_api_client` 函数中添加新提供商的初始化逻辑
3. 如果需要特殊的 API 调用处理，在 `call_llm_api` 函数中添加相应逻辑
4. 更新 `.env.example` 文件添加必要的配置变量
5. 更新 `ONE_API_SETUP.md` 文档，包含新提供商的配置说明
6. 添加必要的测试用例

## 许可证

通过贡献到这个项目，您同意您的贡献将在 MIT 许可证下发布。 