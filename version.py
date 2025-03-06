"""
版本控制模块
跟踪应用程序的版本历史和变更
"""

__version__ = "1.2.0"
__build__ = "20240620"

VERSION_INFO = {
    "version": __version__,
    "build": __build__,
    "name": "RoundTable对话系统",
    "description": "多专家对话和会议系统",
    "db_schema_version": "1.0",
    "api_version": "v1",
    "changelog": {
        "1.2.0": [
            "添加云备份功能",
            "支持AWS S3、Google Cloud Storage和Azure Blob Storage",
            "增强版本管理系统",
            "添加自动变更日志生成",
            "Docker容器内支持自动备份"
        ],
        "1.1.0": [
            "添加版本管理系统",
            "添加数据库迁移功能",
            "添加Docker支持",
            "优化代码结构和文档"
        ],
        "1.0.0": [
            "初始版本",
            "支持多专家对话",
            "支持用户提问和专家回答",
            "支持WebSocket实时对话更新",
            "支持多种LLM API提供商"
        ]
    }
}

def get_version():
    """返回当前版本号"""
    return __version__

def get_version_info():
    """返回完整版本信息"""
    return VERSION_INFO

def get_db_schema_version():
    """返回数据库架构版本"""
    return VERSION_INFO["db_schema_version"]

def is_compatible_with(client_version):
    """检查客户端版本是否与当前版本兼容"""
    # 简单实现：主版本号相同则兼容
    try:
        current_major = int(__version__.split('.')[0])
        client_major = int(client_version.split('.')[0])
        return current_major == client_major
    except (ValueError, IndexError):
        return False 