#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
搜索引擎测试脚本
"""

import os
import sys
from dotenv import load_dotenv
from search_engines import (
    search_with_engine,
    format_search_results,
    search_latest_info_with_engine,
    SearchEngineFactory
)

# 加载环境变量
load_dotenv()

def test_searxng():
    """测试SearXNG搜索引擎"""
    print("\n===== 测试SearXNG搜索引擎 =====")
    
    # 检查SearXNG主机配置
    hostname = os.getenv("SEARXNG_HOSTNAME")
    if not hostname:
        print("警告: 未设置SEARXNG_HOSTNAME环境变量，使用默认值http://localhost:8080")
    else:
        print(f"SearXNG主机: {hostname}")
    
    # 创建SearXNG搜索引擎实例
    engine = SearchEngineFactory.get_search_engine("searxng")
    print(f"搜索引擎名称: {engine.name}")
    print(f"主机地址: {engine.hostname}")
    print(f"安全搜索级别: {engine.safesearch}")
    print(f"搜索引擎列表: {engine.engines}")
    
    # 执行搜索
    query = "人工智能最新发展"
    print(f"\n执行搜索: {query}")
    try:
        results = engine.search(query, language="zh", max_results=3)
        if results:
            print(f"搜索成功，找到 {len(results)} 条结果:")
            print(format_search_results(results))
        else:
            print("搜索未返回结果，可能是SearXNG服务未正确配置或无法访问。")
    except Exception as e:
        print(f"搜索出错: {str(e)}")

def test_tavily():
    """测试Tavily搜索引擎"""
    print("\n===== 测试Tavily搜索引擎 =====")
    
    # 检查Tavily API密钥配置
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("警告: 未设置TAVILY_API_KEY环境变量，Tavily搜索将无法使用")
        return
    else:
        print(f"Tavily API密钥: {api_key[:4]}...{api_key[-4:]} (已设置)")
    
    # 创建Tavily搜索引擎实例
    engine = SearchEngineFactory.get_search_engine("tavily")
    print(f"搜索引擎名称: {engine.name}")
    print(f"API URL: {engine.api_url}")
    
    # 执行搜索
    query = "artificial intelligence latest developments"
    print(f"\n执行搜索: {query}")
    try:
        # 构建请求参数
        search_depth = "basic"  # 可选: "basic" 或 "advanced"
        max_results = 3
        topic = "general"  # 可选: "general", "academic", "news" 等
        
        print(f"搜索深度: {search_depth}")
        print(f"最大结果数: {max_results}")
        print(f"搜索主题: {topic}")
        
        # 执行搜索
        results = engine.search(
            query=query, 
            search_depth=search_depth, 
            max_results=max_results,
            topic=topic
        )
        
        if results:
            print(f"搜索成功，找到 {len(results)} 条结果:")
            print(format_search_results(results))
        else:
            print("搜索未返回结果，可能是API密钥无效或请求失败。")
            print("使用模拟数据:")
            mock_results = get_mock_search_results(query)
            print(format_search_results(mock_results))
    except Exception as e:
        print(f"搜索出错: {str(e)}")
        print("使用模拟数据:")
        mock_results = get_mock_search_results(query)
        print(format_search_results(mock_results))

def test_search_latest_info():
    """测试search_latest_info_with_engine函数"""
    print("\n===== 测试search_latest_info_with_engine函数 =====")
    
    # 从环境变量获取搜索引擎
    engine_name = os.getenv("SEARCH_ENGINE", "searxng")
    print(f"使用搜索引擎: {engine_name}")
    
    # 测试主题
    topics = [
        "人工智能在医疗领域的应用",
        "全球气候变化的最新研究",
        "区块链技术的发展趋势"
    ]
    
    for topic in topics:
        print(f"\n搜索主题: {topic}")
        try:
            # 模拟技能列表
            skills = ["数据分析", "机器学习", "自然语言处理"]
            
            # 执行搜索
            result = search_latest_info_with_engine(
                topic=topic,
                skills=skills,
                engine_name=engine_name,
                max_results=3
            )
            
            print(result)
        except Exception as e:
            print(f"搜索出错: {str(e)}")

def main():
    """主函数"""
    print("===== 搜索引擎测试 =====")
    
    # 测试SearXNG搜索引擎
    test_searxng()
    
    # 测试Tavily搜索引擎
    test_tavily()
    
    # 测试search_latest_info_with_engine函数
    test_search_latest_info()

if __name__ == "__main__":
    main() 