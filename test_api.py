#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API连接测试脚本
用于测试各种LLM API的连接状态
"""

import os
import sys
from dotenv import load_dotenv
from round_table import test_api_connection, init_api_client

# 加载环境变量
load_dotenv()

def main():
    """主函数"""
    print("开始API连接测试...")
    
    # 测试默认提供商
    default_provider = os.getenv("DEFAULT_PROVIDER", "volcengine")
    default_model = os.getenv("DEFAULT_MODEL", "").split(":")[-1]
    if not default_model:
        default_model = "deepseek-r1-250120"
    
    print(f"\n测试默认提供商: {default_provider}, 模型: {default_model}")
    success, response = test_api_connection(default_provider, default_model)
    
    if not success:
        print("\n默认API连接失败，尝试备用模型...")
        backup_model_str = os.getenv("BACKUP_MODEL", "siliconflow:claude-3-opus")
        if ":" in backup_model_str:
            backup_provider, backup_model = backup_model_str.split(":", 1)
            print(f"\n测试备用提供商: {backup_provider}, 模型: {backup_model}")
            success, response = test_api_connection(backup_provider, backup_model)
    
    print("\n测试结果汇总:")
    print(f"默认提供商 ({default_provider}): {'成功' if success else '失败'}")
    
    # 检查环境变量配置
    print("\n环境变量配置检查:")
    print(f"DEFAULT_PROVIDER: {os.getenv('DEFAULT_PROVIDER', '未设置')}")
    print(f"DEFAULT_MODEL: {os.getenv('DEFAULT_MODEL', '未设置')}")
    print(f"BACKUP_MODEL: {os.getenv('BACKUP_MODEL', '未设置')}")
    print(f"MAX_RETRIES: {os.getenv('MAX_RETRIES', '未设置')}")
    print(f"TIMEOUT: {os.getenv('TIMEOUT', '未设置')}")
    print(f"API_TIMEOUT: {os.getenv('API_TIMEOUT', '未设置')}")
    
    # 检查API密钥
    volcengine_key = os.getenv("VOLCENGINE_API_KEY", "")
    print(f"VOLCENGINE_API_KEY: {'已设置' if volcengine_key else '未设置'}")
    
    siliconflow_key = os.getenv("SILICONFLOW_API_KEY", "")
    print(f"SILICONFLOW_API_KEY: {'已设置' if siliconflow_key else '未设置'}")
    
    # 提供建议
    print("\n建议:")
    if not success:
        print("- API连接测试失败，请检查网络连接和API密钥")
        print("- 考虑更换API提供商或模型")
        print("- 增加超时时间和重试次数")
    else:
        print("- API连接测试成功，但在实际使用中可能仍会遇到超时")
        print("- 建议减少会议中的代理数量或讨论轮数")
        print("- 考虑简化提示词，减少生成内容的长度")

if __name__ == "__main__":
    main() 