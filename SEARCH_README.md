# RoundTable 搜索引擎功能

本文档介绍如何在RoundTable项目中设置和使用搜索引擎功能，使agents能够获取最新信息。

## 功能概述

RoundTable现在支持以下搜索引擎：

1. **SearXNG** - 一个免费的元搜索引擎，不需要API密钥
2. **Tavily** - 一个专为AI优化的搜索API

搜索功能允许agents在生成回复时引用最新的信息，使讨论更加丰富和有信息量。

## 安装依赖

确保安装了必要的依赖：

```bash
pip install requests
```

## 配置搜索引擎

### 基本配置

在`.env`文件中添加以下配置：

```bash
# 搜索引擎设置
# ====================
# 是否启用搜索功能
ENABLE_SEARCH=true
# 默认搜索引擎，支持searxng和tavily
SEARCH_ENGINE=searxng
# 搜索结果数量
SEARCH_MAX_RESULTS=5
```

### SearXNG配置

SearXNG是一个自托管的元搜索引擎，需要先安装并运行SearXNG服务。

1. 安装SearXNG：
   - 使用Docker：[searxng-docker](https://github.com/searxng/searxng-docker)
   - 或直接安装：[SearXNG安装指南](https://docs.searxng.org/admin/installation.html)

2. 配置SearXNG：
   - 确保在`settings.yml`中启用JSON格式：
     ```yaml
     search:
         formats:
             - html
             - json
     ```
   - 关闭限制器：
     ```yaml
     server:
        limiter: false # 默认为true
     ```

3. 在`.env`文件中添加SearXNG配置：
   ```bash
   # SearXNG搜索引擎设置
   SEARXNG_HOSTNAME=http://localhost:8080
   SEARXNG_SAFE=0
   SEARXNG_ENGINES=google,bing,duckduckgo
   SEARXNG_LANGUAGE=zh
   ```

### Tavily配置

Tavily是一个专为AI优化的搜索API，需要API密钥。

1. 注册Tavily账号：[Tavily官网](https://tavily.com/)
2. 获取API密钥（在Tavily控制台中可以找到）
3. 在`.env`文件中添加Tavily配置：
   ```bash
   # Tavily搜索引擎设置
   TAVILY_API_KEY=your_tavily_api_key_here
   ```

Tavily API提供两种搜索深度：
- `basic`：基本搜索，适合一般查询，API消耗较少
- `advanced`：高级搜索，提供更深入的结果，API消耗较多

默认使用`basic`搜索深度。如果需要更深入的搜索结果，可以在代码中指定`search_depth="advanced"`。

**重要说明**：
- Tavily API要求将API密钥放在请求头的`Authorization`字段中，格式为`Bearer your_api_key`
- 当前的API端点是`https://api.tavily.com/search`
- Tavily API支持多种参数，包括：
  - `query`：搜索查询
  - `search_depth`：搜索深度（basic或advanced）
  - `max_results`：最大结果数
  - `include_answer`：是否包含AI生成的回答
  - `topic`：搜索主题（如general、academic、news等）
- Tavily API是一个付费服务，有免费层级（通常每月有一定数量的免费请求）
- 请查看[Tavily API文档](https://docs.tavily.com/)获取最新的API规范
- 查看[Tavily定价页面](https://tavily.com/#pricing)了解最新的定价信息

## 测试搜索功能

使用提供的测试脚本测试搜索功能：

```bash
python test_search.py
```

这将测试SearXNG和Tavily搜索引擎，以及`search_latest_info_with_engine`函数。

## 使用搜索功能

搜索功能已集成到`generate_agent_speech`函数中，agents在生成回复时会自动搜索相关信息。

如果要禁用搜索功能，可以在`.env`文件中设置：

```bash
ENABLE_SEARCH=false
```

## 模拟搜索数据

如果无法连接到实际的搜索引擎（如SearXNG服务未运行），系统会自动使用模拟数据功能。这个功能会根据搜索查询生成相关的模拟搜索结果，确保即使在没有外部搜索引擎的情况下，agents也能获取"最新"信息。

模拟数据功能支持以下主题类别：
- 人工智能/AI相关主题
- 气候/环境相关主题
- 经济/金融相关主题
- 其他通用主题

要使用模拟数据而不是实际搜索，您可以：
1. 不安装或不启动SearXNG服务
2. 确保`.env`文件中`ENABLE_SEARCH=true`

系统会在无法连接到搜索引擎时自动切换到模拟数据模式。

## 深度研究功能（未来计划）

未来计划实现类似search_with_ai项目的深度研究功能，包括：

1. 分析用户查询
2. 生成跟进问题
3. 执行搜索查询
4. 分析搜索结果
5. 递归探索
6. 生成综合报告

## 故障排除

### SearXNG连接问题

如果无法连接到SearXNG：

1. 确保SearXNG服务正在运行
2. 检查`SEARXNG_HOSTNAME`配置是否正确
3. 确保网络连接正常

### Tavily API问题

如果Tavily API返回错误：

1. **401错误**：API密钥无效或未提供
   - 确保API密钥正确
   - 检查API密钥是否已过期
   - 确保API密钥已正确设置在`.env`文件中
   - 确保API密钥在请求头的`Authorization`字段中正确传递，格式为`Bearer your_api_key`

2. **404错误**：API端点不存在
   - 确保使用的是最新的Tavily API端点（`https://api.tavily.com/search`）
   - 检查API文档是否有更新，端点可能已更改
   - 确保URL拼写正确，没有多余的斜杠或路径

3. **429错误**：超出API请求限制
   - 检查您的Tavily账户使用情况
   - 考虑升级您的Tavily计划
   - 实现请求限制和重试逻辑

4. **400错误**：请求参数错误
   - 检查请求参数是否符合API要求
   - 确保必填字段已提供
   - 检查参数类型是否正确（如数字、布尔值等）

5. **405错误**：方法不允许
   - 这通常是由于HTTP方法不正确导致的
   - 确保使用POST请求而不是GET请求

6. **其他错误**：
   - 查看Tavily控制台中的错误日志
   - 检查Tavily API文档是否有更新
   - 联系Tavily支持团队获取帮助

如果遇到问题，系统会自动切换到使用模拟数据，确保功能不会中断。

## 参考资料

- [SearXNG文档](https://docs.searxng.org/)
- [Tavily API文档](https://docs.tavily.com/)
- [search_with_ai项目](https://github.com/yokingma/search_with_ai) 