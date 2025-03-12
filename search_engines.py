import os
import json
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

# 搜索结果接口
class SearchResult:
    def __init__(self, title: str, url: str, snippet: str, source: str = None):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source
    
    def __str__(self):
        return f"{self.title}\n{self.url}\n{self.snippet}"

# 搜索引擎基类
class SearchEngine:
    def __init__(self):
        self.name = "Base Search Engine"
    
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        """执行搜索并返回结果列表"""
        raise NotImplementedError("子类必须实现search方法")

# SearXNG搜索引擎
class SearXNGSearch(SearchEngine):
    def __init__(self):
        super().__init__()
        self.name = "SearXNG"
        # 从环境变量获取SearXNG主机地址，默认为localhost:8080
        self.hostname = os.getenv("SEARXNG_HOSTNAME", "http://localhost:8080")
        # 从环境变量获取安全搜索级别，默认为0（关闭）
        self.safesearch = int(os.getenv("SEARXNG_SAFE", "0"))
        # 从环境变量获取搜索引擎列表
        self.engines = os.getenv("SEARXNG_ENGINES", "").split(",")
        self.engines = [e.strip() for e in self.engines if e.strip()]
    
    def search(self, query: str, language: str = "all", 
               categories: List[str] = None, 
               max_results: int = 5, **kwargs) -> List[SearchResult]:
        """
        使用SearXNG执行搜索
        
        参数:
            query: 搜索查询
            language: 搜索语言，默认为all
            categories: 搜索类别列表，默认为["general"]
            max_results: 最大结果数，默认为5
        
        返回:
            SearchResult对象列表
        """
        if not query.strip():
            return []
        
        if categories is None:
            categories = ["general"]
        
        try:
            # 构建请求参数
            params = {
                "q": query,
                "format": "json",
                "categories": ",".join(categories),
                "language": language,
                "safesearch": self.safesearch
            }
            
            # 如果有指定引擎，添加到参数中
            if self.engines:
                params["engines"] = ",".join(self.engines)
            
            # 发送请求
            response = requests.post(
                f"{self.hostname}/search",
                data=params,
                timeout=10
            )
            
            # 检查响应状态
            if response.status_code != 200:
                print(f"SearXNG搜索失败: HTTP {response.status_code}")
                return []
            
            # 解析结果
            result = response.json()
            if not result.get("results"):
                return []
            
            # 转换为SearchResult对象
            search_results = []
            for item in result["results"][:max_results]:
                search_results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    source=item.get("engine", "")
                ))
            
            return search_results
        
        except Exception as e:
            print(f"SearXNG搜索出错: {str(e)}")
            return []

# Tavily搜索引擎
class TavilySearch(SearchEngine):
    def __init__(self):
        super().__init__()
        self.name = "Tavily"
        # 从环境变量获取Tavily API密钥
        self.api_key = os.getenv("TAVILY_API_KEY", "")
        if not self.api_key:
            print("警告: 未设置TAVILY_API_KEY环境变量")
        
        # 使用官方API端点
        self.api_url = "https://api.tavily.com/search"
    
    def search(self, query: str, search_depth: str = "basic", 
               max_results: int = 5, **kwargs) -> List[SearchResult]:
        """
        使用Tavily执行搜索
        
        参数:
            query: 搜索查询
            search_depth: 搜索深度，可选值为"basic"或"advanced"，默认为"basic"
            max_results: 最大结果数，默认为5
        
        返回:
            SearchResult对象列表
        """
        if not query.strip() or not self.api_key:
            return []
        
        try:
            # 构建请求参数 - 根据官方API文档
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 构建请求体
            payload = {
                "query": query,
                "search_depth": search_depth,
                "max_results": max_results,
                "include_answer": True,
                "include_domains": kwargs.get("include_domains", []),
                "exclude_domains": kwargs.get("exclude_domains", []),
                "include_raw_content": False,
                "include_images": False
            }
            
            # 如果提供了主题，添加到请求中
            if "topic" in kwargs:
                payload["topic"] = kwargs["topic"]
            else:
                payload["topic"] = "general"
            
            # 打印调试信息
            print(f"Tavily API URL: {self.api_url}")
            print(f"Tavily API请求参数: {payload}")
            
            # 发送POST请求
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=15
            )
            
            # 检查响应状态
            if response.status_code != 200:
                print(f"Tavily搜索失败: HTTP {response.status_code}")
                print(f"响应内容: {response.text}")
                
                if response.status_code == 401:
                    print("API密钥无效或未提供")
                elif response.status_code == 429:
                    print("超出API请求限制")
                elif response.status_code == 404:
                    print("API端点不存在，请检查URL是否正确")
                return []
            
            # 解析结果
            result = response.json()
            
            # 检查是否有结果
            search_results = []
            
            # 如果API返回了answer，添加为第一个结果
            if result.get("answer"):
                search_results.append(SearchResult(
                    title="Tavily AI生成的回答",
                    url="https://tavily.com/",
                    snippet=result.get("answer", ""),
                    source="Tavily AI"
                ))
            
            # 添加搜索结果
            if result.get("results"):
                for item in result["results"]:
                    search_results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("content", ""),
                        source="Tavily"
                    ))
            
            if not search_results:
                print("Tavily API返回成功，但没有搜索结果")
            
            return search_results
        
        except Exception as e:
            print(f"Tavily搜索出错: {str(e)}")
            return []

# 搜索引擎工厂
class SearchEngineFactory:
    @staticmethod
    def get_search_engine(engine_name: str) -> SearchEngine:
        """
        根据引擎名称获取搜索引擎实例
        
        参数:
            engine_name: 搜索引擎名称，支持"searxng"和"tavily"
        
        返回:
            SearchEngine实例
        """
        engine_name = engine_name.lower()
        
        if engine_name == "searxng":
            return SearXNGSearch()
        elif engine_name == "tavily":
            return TavilySearch()
        else:
            # 默认使用SearXNG
            print(f"未知的搜索引擎: {engine_name}，使用默认的SearXNG")
            return SearXNGSearch()

# 主搜索函数
def search_with_engine(query: str, engine_name: str = None, **kwargs) -> List[SearchResult]:
    """
    使用指定的搜索引擎执行搜索
    
    参数:
        query: 搜索查询
        engine_name: 搜索引擎名称，如果为None则使用环境变量SEARCH_ENGINE指定的引擎，默认为"searxng"
        **kwargs: 传递给搜索引擎的其他参数
    
    返回:
        SearchResult对象列表
    """
    # 如果未指定引擎，从环境变量获取
    if engine_name is None:
        engine_name = os.getenv("SEARCH_ENGINE", "searxng")
    
    # 获取搜索引擎实例
    engine = SearchEngineFactory.get_search_engine(engine_name)
    
    # 执行搜索
    try:
        results = engine.search(query, **kwargs)
        if results:
            return results
        else:
            print(f"搜索未返回结果，使用模拟数据")
            return get_mock_search_results(query)
    except Exception as e:
        print(f"搜索出错: {str(e)}，使用模拟数据")
        return get_mock_search_results(query)

# 生成模拟搜索结果
def get_mock_search_results(query: str) -> List[SearchResult]:
    """
    生成模拟搜索结果
    
    参数:
        query: 搜索查询
    
    返回:
        SearchResult对象列表
    """
    current_date = datetime.now().strftime("%Y年%m月%d日")
    results = []
    
    # 根据查询内容生成不同的模拟结果
    if "人工智能" in query or "AI" in query:
        results.append(SearchResult(
            title="人工智能最新发展趋势报告",
            url="https://example.com/ai-trends",
            snippet=f"截至{current_date}，大型语言模型在多模态理解和推理能力方面取得了显著进展。多家科技巨头发布了新一代AI模型，在医疗、教育和科研领域的应用不断扩大。",
            source="模拟数据"
        ))
        results.append(SearchResult(
            title="AI在医疗领域的突破性应用",
            url="https://example.com/ai-medical",
            snippet="人工智能技术在医疗诊断、药物研发和个性化治疗方案制定方面展现出巨大潜力。最新研究表明，AI辅助诊断系统在某些疾病检测中的准确率已超过人类专家。",
            source="模拟数据"
        ))
        results.append(SearchResult(
            title="AI伦理与监管框架的最新进展",
            url="https://example.com/ai-ethics",
            snippet="随着AI技术的快速发展，各国政府正在加紧制定AI监管框架，平衡创新与安全。关键议题包括数据隐私、算法透明度、责任归属和防止滥用。",
            source="模拟数据"
        ))
    elif "气候" in query or "环境" in query:
        results.append(SearchResult(
            title="全球气候变化最新监测数据",
            url="https://example.com/climate-data",
            snippet=f"截至{current_date}的监测数据显示，全球平均温度继续上升，极端天气事件频率增加。科学家警告，如不采取更积极的减排措施，将难以实现《巴黎协定》的目标。",
            source="模拟数据"
        ))
        results.append(SearchResult(
            title="可再生能源发展突破性进展",
            url="https://example.com/renewable-energy",
            snippet="太阳能和风能技术成本持续下降，效率提高，使可再生能源在多个国家已成为最经济的能源选择。储能技术的进步正在解决间歇性问题。",
            source="模拟数据"
        ))
        results.append(SearchResult(
            title="碳捕获技术的创新与应用",
            url="https://example.com/carbon-capture",
            snippet="新一代碳捕获技术效率提高、成本降低，正在从实验室走向商业化应用。多国政府增加了对这一关键气候解决方案的投资支持。",
            source="模拟数据"
        ))
    elif "经济" in query or "金融" in query:
        results.append(SearchResult(
            title="全球经济最新趋势分析",
            url="https://example.com/economy-trends",
            snippet=f"{current_date}发布的经济数据显示，全球经济增长放缓但仍保持韧性。通胀压力有所缓解，但地区差异明显。供应链重组和数字化转型正在重塑全球经济格局。",
            source="模拟数据"
        ))
        results.append(SearchResult(
            title="金融市场波动与投资策略",
            url="https://example.com/financial-markets",
            snippet="近期金融市场波动加剧，投资者需要更加谨慎。分析师建议多元化配置资产，关注科技创新、可持续发展和医疗健康等长期增长领域。",
            source="模拟数据"
        ))
        results.append(SearchResult(
            title="数字货币与金融科技发展报告",
            url="https://example.com/fintech-report",
            snippet="数字货币和区块链技术正在改变传统金融服务。中央银行数字货币(CBDC)研发加速，同时监管机构加强了对加密资产市场的监管。",
            source="模拟数据"
        ))
    else:
        # 通用模拟结果
        results.append(SearchResult(
            title=f"{query}的最新研究进展",
            url=f"https://example.com/{query.replace(' ', '-')}",
            snippet=f"关于{query}的最新研究表明，该领域正在经历快速发展和创新。专家们正在探索新方法和技术，以解决长期存在的挑战并开拓新的可能性。",
            source="模拟数据"
        ))
        results.append(SearchResult(
            title=f"{query}行业趋势分析",
            url=f"https://example.com/{query.replace(' ', '-')}-trends",
            snippet=f"{query}相关产业正经历数字化转型，企业正在采用创新技术和商业模式以保持竞争力。专家预测，未来几年该领域将继续快速发展。",
            source="模拟数据"
        ))
        results.append(SearchResult(
            title=f"{query}全球合作与发展",
            url=f"https://example.com/{query.replace(' ', '-')}-cooperation",
            snippet=f"国际组织和研究机构正在加强{query}领域的合作，共享知识和资源以应对共同挑战。跨学科合作正在产生创新解决方案。",
            source="模拟数据"
        ))
    
    return results

# 格式化搜索结果为字符串
def format_search_results(results: List[SearchResult], 
                          include_source: bool = True) -> str:
    """
    将搜索结果格式化为字符串
    
    参数:
        results: SearchResult对象列表
        include_source: 是否包含来源信息
    
    返回:
        格式化后的字符串
    """
    if not results:
        return "未找到相关信息。"
    
    current_date = datetime.now().strftime("%Y年%m月%d日")
    formatted = f"搜索时间: {current_date}\n\n"
    
    for i, result in enumerate(results, 1):
        formatted += f"{i}. {result.title}\n"
        formatted += f"   URL: {result.url}\n"
        formatted += f"   摘要: {result.snippet}\n"
        if include_source and result.source:
            formatted += f"   来源: {result.source}\n"
        formatted += "\n"
    
    return formatted

# 主搜索函数，返回格式化的字符串结果
def search_latest_info_with_engine(topic: str, skills: List[str] = None, 
                                  engine_name: str = None, 
                                  max_results: int = 5) -> str:
    """
    搜索最新信息并返回格式化的结果
    
    参数:
        topic: 搜索主题
        skills: 技能列表，用于优化搜索查询
        engine_name: 搜索引擎名称
        max_results: 最大结果数
    
    返回:
        格式化后的搜索结果字符串
    """
    # 构建搜索查询
    query = topic
    if skills and len(skills) > 0:
        # 最多使用3个技能来优化查询
        selected_skills = skills[:3]
        query += " " + " ".join(selected_skills)
    
    # 执行搜索
    results = search_with_engine(
        query=query,
        engine_name=engine_name,
        max_results=max_results
    )
    
    # 格式化结果
    return format_search_results(results)

# 测试代码
if __name__ == "__main__":
    # 测试SearXNG搜索
    print("测试SearXNG搜索:")
    results = search_with_engine("人工智能最新发展", "searxng")
    print(format_search_results(results))
    
    # 测试Tavily搜索（需要设置API密钥）
    if os.getenv("TAVILY_API_KEY"):
        print("\n测试Tavily搜索:")
        results = search_with_engine("artificial intelligence latest developments", "tavily")
        print(format_search_results(results)) 