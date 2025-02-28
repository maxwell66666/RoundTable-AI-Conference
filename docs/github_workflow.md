# RoundTable GitHub工作流程指南

本文档介绍如何使用GitHub进行RoundTable项目的代码管理、版本控制和自动化发布。

## 目录

- [分支管理策略](#分支管理策略)
- [提交信息规范](#提交信息规范)
- [发布流程](#发布流程)
- [自动化工作流](#自动化工作流)
- [安全实践](#安全实践)
- [GitHub与云备份集成](#github与云备份集成)

## 分支管理策略

采用Git Flow分支管理策略:

- `master`: 生产环境稳定分支
- `develop`: 开发分支，包含最新功能
- `feature/*`: 新功能分支
- `bugfix/*`: 问题修复分支
- `release/*`: 版本发布准备分支
- `hotfix/*`: 紧急生产环境修复分支

### 分支工作流

```
master ─────────────────●───────────●─────
                        ↑           ↑
release    ────────────●───────────●─────
                      ↑           ↑
develop  ──●────●────●────●───────●─────
          ↑    ↑    ↑    ↑ 
feature   ●────●    ●────●
```

## 提交信息规范

采用[约定式提交规范](https://www.conventionalcommits.org/zh-hans/v1.0.0/):

```
<类型>[可选的作用域]: <描述>

[可选的正文]

[可选的脚注]
```

类型包括:
- `feat`: 新功能
- `fix`: 问题修复
- `docs`: 文档变更
- `style`: 代码风格变更(不影响功能)
- `refactor`: 代码重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建过程或辅助工具变更

示例:
```
feat(对话): 添加实时更新功能

- 使用WebSocket实现实时对话更新
- 添加进度指示器
- 优化消息队列处理

Closes #123
```

## 发布流程

1. **从develop分支创建release分支**
   ```bash
   git checkout develop
   git pull
   git checkout -b release/v1.3.0
   ```

2. **准备发布内容**
   - 更新版本号和变更日志
   ```bash
   python release.py bump --type minor --auto-changelog
   ```
   - 进行最终测试和bug修复
   - 更新文档

3. **合并到master分支**
   ```bash
   git checkout master
   git merge --no-ff release/v1.3.0
   git tag -a v1.3.0 -m "版本1.3.0"
   ```

4. **同步回develop分支**
   ```bash
   git checkout develop
   git merge --no-ff release/v1.3.0
   ```

5. **推送变更和标签**
   ```bash
   git push origin master develop
   git push origin --tags
   ```

## 自动化工作流

RoundTable项目使用GitHub Actions自动化以下任务:

### 持续集成

`.github/workflows/ci-cd.yml` 负责:
- 代码风格检查
- 单元测试执行
- Docker镜像构建与发布

### 自动备份

`.github/workflows/backup.yml` 负责:
- 定期自动备份
- 生成变更日志
- 版本信息维护

## 安全实践

使用GitHub Secrets存储敏感信息:

1. 在GitHub仓库设置中添加以下Secrets:
   - `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN`: Docker Hub凭证
   - `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`: AWS凭证
   - `GCP_CREDENTIALS`: GCP凭证(Base64编码)
   - `AZURE_CONNECTION_STRING`: Azure凭证

2. **永远不要**提交敏感信息到代码库:
   - API密钥
   - 密码和密钥
   - 连接字符串
   - 证书

## GitHub与云备份集成

GitHub主要用于代码版本控制，而不是数据和配置备份。

### 云备份策略

1. **代码管理**: 通过GitHub进行
   - 应用代码
   - 文档
   - 迁移脚本
   - 配置模板

2. **数据备份**: 通过云存储进行
   - 数据库文件
   - 用户数据
   - 配置文件
   - 媒体文件

### 集成自动化

1. GitHub Actions可以触发备份流程
2. 版本发布时自动创建备份
3. 主要数据仍使用专用云存储服务

### 灾难恢复流程

1. 从GitHub克隆最新代码
2. 从云存储恢复最新备份
3. 运行迁移脚本更新数据库结构
4. 部署应用 