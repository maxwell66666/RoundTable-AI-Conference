#!/usr/bin/env python3
"""
备份模块
负责数据库备份和云存储集成
"""

import os
import sys
import json
import shutil
import sqlite3
import argparse
import logging
import tarfile
import zipfile
import datetime
import configparser
from pathlib import Path
from io import BytesIO
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("backup.log")
    ]
)
logger = logging.getLogger("backup")

# 备份配置
DEFAULT_CONFIG = {
    "general": {
        "backup_dir": "backups",
        "retention_days": os.getenv("BACKUP_RETENTION_DAYS", "30"),
        "compress_format": "tar.gz",  # 或 "zip"
        "include_dialogues": "True",
    },
    "schedule": {
        "enabled": os.getenv("ENABLE_AUTO_BACKUP", "False").lower() == "true",
        "interval_hours": "24",
        "backup_time": "02:00",  # 24小时制，深夜2点
    },
    "aws": {
        "enabled": "True" if os.getenv("AWS_ACCESS_KEY_ID") else "False",
        "access_key": os.getenv("AWS_ACCESS_KEY_ID", ""),
        "secret_key": os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        "region": os.getenv("AWS_REGION", "us-east-1"),
        "bucket": os.getenv("AWS_BUCKET", "roundtable-backups"),
        "prefix": os.getenv("AWS_PREFIX", "backups/"),
    },
    "gcp": {
        "enabled": "True" if os.getenv("GCP_CREDENTIALS_FILE") else "False",
        "credentials_file": os.getenv("GCP_CREDENTIALS_FILE", "gcp-credentials.json"),
        "bucket": os.getenv("GCP_BUCKET", "roundtable-backups"),
        "prefix": os.getenv("GCP_PREFIX", "backups/"),
    },
    "azure": {
        "enabled": "True" if os.getenv("AZURE_CONNECTION_STRING") else "False",
        "connection_string": os.getenv("AZURE_CONNECTION_STRING", ""),
        "container": os.getenv("AZURE_CONTAINER", "roundtable-backups"),
        "prefix": os.getenv("AZURE_PREFIX", "backups/"),
    }
}

CONFIG_FILE = "backup_config.ini"

def load_config():
    """加载备份配置"""
    if not os.path.exists(CONFIG_FILE):
        # 如果配置文件不存在，创建默认配置
        logger.info(f"配置文件 {CONFIG_FILE} 不存在，创建默认配置")
        config = configparser.ConfigParser()
        for section, options in DEFAULT_CONFIG.items():
            config[section] = options
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
    else:
        # 配置文件存在，但我们仍然要应用环境变量中的设置
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE, encoding='utf-8')
        
        # 应用环境变量设置
        if os.getenv("BACKUP_RETENTION_DAYS"):
            config["general"]["retention_days"] = os.getenv("BACKUP_RETENTION_DAYS")
        
        # 更新AWS配置
        if os.getenv("AWS_ACCESS_KEY_ID"):
            config["aws"]["enabled"] = "True"
            config["aws"]["access_key"] = os.getenv("AWS_ACCESS_KEY_ID")
            config["aws"]["secret_key"] = os.getenv("AWS_SECRET_ACCESS_KEY", "")
            if os.getenv("AWS_REGION"):
                config["aws"]["region"] = os.getenv("AWS_REGION")
            if os.getenv("AWS_BUCKET"):
                config["aws"]["bucket"] = os.getenv("AWS_BUCKET")
            if os.getenv("AWS_PREFIX"):
                config["aws"]["prefix"] = os.getenv("AWS_PREFIX")
        
        # 更新GCP配置
        if os.getenv("GCP_CREDENTIALS_FILE"):
            config["gcp"]["enabled"] = "True"
            config["gcp"]["credentials_file"] = os.getenv("GCP_CREDENTIALS_FILE")
            if os.getenv("GCP_BUCKET"):
                config["gcp"]["bucket"] = os.getenv("GCP_BUCKET")
            if os.getenv("GCP_PREFIX"):
                config["gcp"]["prefix"] = os.getenv("GCP_PREFIX")
        
        # 更新Azure配置
        if os.getenv("AZURE_CONNECTION_STRING"):
            config["azure"]["enabled"] = "True"
            config["azure"]["connection_string"] = os.getenv("AZURE_CONNECTION_STRING")
            if os.getenv("AZURE_CONTAINER"):
                config["azure"]["container"] = os.getenv("AZURE_CONTAINER")
            if os.getenv("AZURE_PREFIX"):
                config["azure"]["prefix"] = os.getenv("AZURE_PREFIX")
        
        # 自动备份设置
        if os.getenv("ENABLE_AUTO_BACKUP"):
            config["schedule"]["enabled"] = os.getenv("ENABLE_AUTO_BACKUP").lower() == "true"
        
        # 保存更新后的配置
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
    
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')
    return config

def get_db_files():
    """获取所有数据库文件"""
    return [f for f in os.listdir() if f.endswith('.db')]

def get_dialogue_files():
    """获取所有对话历史文件"""
    return [f for f in os.listdir() if f.startswith('dialogue_history_') and f.endswith('.json')]

def create_backup_name():
    """创建备份文件名"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    from version import get_version
    version = get_version()
    return f"roundtable_v{version}_{timestamp}"

def create_backup_archive(config):
    """创建备份归档文件"""
    backup_dir = config['general']['backup_dir']
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # 收集要备份的文件
    db_files = get_db_files()
    
    # 检查是否包含对话历史
    include_dialogues = config.getboolean('general', 'include_dialogues')
    dialogue_files = get_dialogue_files() if include_dialogues else []
    
    # 收集需要备份的额外配置文件
    config_files = ['.env', 'backup_config.ini', 'version.py']
    config_files = [f for f in config_files if os.path.exists(f)]
    
    all_files = db_files + dialogue_files + config_files
    
    # 检查文件是否存在
    if not all_files:
        logger.error("没有找到任何文件进行备份")
        return None
    
    # 创建备份文件名
    backup_name = create_backup_name()
    compress_format = config['general']['compress_format']
    
    if compress_format == "tar.gz":
        # 创建tar.gz归档
        archive_path = os.path.join(backup_dir, f"{backup_name}.tar.gz")
        with tarfile.open(archive_path, "w:gz") as tar:
            for file in all_files:
                logger.info(f"添加文件到备份: {file}")
                tar.add(file)
    else:
        # 创建zip归档
        archive_path = os.path.join(backup_dir, f"{backup_name}.zip")
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in all_files:
                logger.info(f"添加文件到备份: {file}")
                zipf.write(file)
    
    logger.info(f"备份归档已创建: {archive_path}")
    return archive_path

def upload_to_aws(config, archive_path):
    """上传备份到AWS S3"""
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        if not config.getboolean('aws', 'enabled'):
            logger.info("AWS备份未启用")
            return False
        
        logger.info("开始上传备份到AWS S3...")
        
        # 设置AWS凭证
        access_key = config['aws']['access_key']
        secret_key = config['aws']['secret_key']
        region = config['aws']['region']
        bucket = config['aws']['bucket']
        prefix = config['aws']['prefix']
        
        if not access_key or not secret_key:
            logger.error("AWS凭证未配置")
            return False
        
        # 创建S3客户端
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        # 上传文件
        file_name = os.path.basename(archive_path)
        object_name = f"{prefix}{file_name}"
        
        try:
            s3_client.upload_file(archive_path, bucket, object_name)
            logger.info(f"成功上传备份到 s3://{bucket}/{object_name}")
            return True
        except ClientError as e:
            logger.error(f"上传到AWS S3失败: {e}")
            return False
            
    except ImportError:
        logger.error("未安装boto3库，无法上传到AWS S3。请运行 'pip install boto3'")
        return False

def upload_to_gcp(config, archive_path):
    """上传备份到Google Cloud Storage"""
    try:
        from google.cloud import storage
        from google.auth.exceptions import DefaultCredentialsError
        
        if not config.getboolean('gcp', 'enabled'):
            logger.info("GCP备份未启用")
            return False
        
        logger.info("开始上传备份到Google Cloud Storage...")
        
        # 设置GCP凭证
        credentials_file = config['gcp']['credentials_file']
        bucket_name = config['gcp']['bucket']
        prefix = config['gcp']['prefix']
        
        if credentials_file and os.path.exists(credentials_file):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_file
        
        # 创建Storage客户端
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            
            # 上传文件
            file_name = os.path.basename(archive_path)
            blob = bucket.blob(f"{prefix}{file_name}")
            
            blob.upload_from_filename(archive_path)
            logger.info(f"成功上传备份到 gs://{bucket_name}/{prefix}{file_name}")
            return True
        except DefaultCredentialsError as e:
            logger.error(f"GCP凭证错误: {e}")
            return False
            
    except ImportError:
        logger.error("未安装google-cloud-storage库，无法上传到GCP。请运行 'pip install google-cloud-storage'")
        return False

def upload_to_azure(config, archive_path):
    """上传备份到Azure Blob Storage"""
    try:
        from azure.storage.blob import BlobServiceClient
        from azure.core.exceptions import ResourceExistsError
        
        if not config.getboolean('azure', 'enabled'):
            logger.info("Azure备份未启用")
            return False
        
        logger.info("开始上传备份到Azure Blob Storage...")
        
        # 设置Azure凭证
        connection_string = config['azure']['connection_string']
        container_name = config['azure']['container']
        prefix = config['azure']['prefix']
        
        if not connection_string:
            logger.error("Azure连接字符串未配置")
            return False
        
        # 创建Blob客户端
        try:
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            
            # 确保容器存在
            try:
                container_client = blob_service_client.create_container(container_name)
            except ResourceExistsError:
                container_client = blob_service_client.get_container_client(container_name)
            
            # 上传文件
            file_name = os.path.basename(archive_path)
            blob_name = f"{prefix}{file_name}"
            blob_client = blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            
            with open(archive_path, "rb") as data:
                blob_client.upload_blob(data)
            
            logger.info(f"成功上传备份到Azure: {container_name}/{blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"上传到Azure失败: {e}")
            return False
            
    except ImportError:
        logger.error("未安装azure-storage-blob库，无法上传到Azure。请运行 'pip install azure-storage-blob'")
        return False

def clean_old_backups(config):
    """清理旧的备份文件"""
    backup_dir = config['general']['backup_dir']
    retention_days = int(config['general']['retention_days'])
    
    if not os.path.exists(backup_dir):
        return
    
    # 计算阈值时间
    now = datetime.datetime.now()
    threshold = now - datetime.timedelta(days=retention_days)
    
    # 遍历备份目录中的所有文件
    for filename in os.listdir(backup_dir):
        file_path = os.path.join(backup_dir, filename)
        
        # 检查文件是否为备份文件
        if (filename.startswith("roundtable_v") and 
            (filename.endswith(".tar.gz") or filename.endswith(".zip"))):
            
            # 获取文件修改时间
            file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            
            # 如果文件超过保留期限，则删除
            if file_mtime < threshold:
                logger.info(f"删除过期备份: {filename}")
                os.remove(file_path)

def create_schedule_script():
    """创建定时备份的调度脚本"""
    # 为不同平台创建调度脚本
    if os.name == 'nt':  # Windows
        script_content = """@echo off
REM 定时备份脚本 - Windows版
python backup.py create
"""
        with open("schedule_backup.bat", "w") as f:
            f.write(script_content)
        logger.info("已创建Windows调度脚本: schedule_backup.bat")
        logger.info("请使用Windows任务计划程序设置定时运行")
        
    else:  # Linux/Mac
        script_content = """#!/bin/bash
# 定时备份脚本 - Linux/Mac版
python3 backup.py create
"""
        script_path = "schedule_backup.sh"
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)  # 添加执行权限
        logger.info(f"已创建Linux/Mac调度脚本: {script_path}")
        logger.info("请使用crontab设置定时运行")
        logger.info("示例 (每天2:00运行): 0 2 * * * cd /path/to/roundtable && ./schedule_backup.sh")

def run_backup():
    """运行备份流程"""
    config = load_config()
    
    # 创建备份归档
    archive_path = create_backup_archive(config)
    if not archive_path:
        return False
    
    # 上传到云存储 (如果启用)
    if config.getboolean('aws', 'enabled'):
        upload_to_aws(config, archive_path)
    
    if config.getboolean('gcp', 'enabled'):
        upload_to_gcp(config, archive_path)
    
    if config.getboolean('azure', 'enabled'):
        upload_to_azure(config, archive_path)
    
    # 清理旧备份
    clean_old_backups(config)
    
    return True

def restore_backup(backup_file):
    """从备份文件恢复数据"""
    if not os.path.exists(backup_file):
        logger.error(f"备份文件不存在: {backup_file}")
        return False
    
    # 创建临时目录
    tmp_dir = "tmp_restore"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir)
    
    try:
        # 解压备份文件
        if backup_file.endswith(".tar.gz"):
            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(path=tmp_dir)
        elif backup_file.endswith(".zip"):
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                zipf.extractall(path=tmp_dir)
        else:
            logger.error(f"不支持的备份文件格式: {backup_file}")
            return False
        
        # 停止应用程序 (实际部署时可能需要)
        logger.info("准备恢复数据...")
        
        # 恢复数据库文件
        for db_file in [f for f in os.listdir(tmp_dir) if f.endswith('.db')]:
            src = os.path.join(tmp_dir, db_file)
            # 如果当前目录中存在此数据库，先备份
            if os.path.exists(db_file):
                backup_name = f"{db_file}.bak.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                shutil.copy2(db_file, backup_name)
                logger.info(f"已备份现有数据库: {backup_name}")
            # 复制恢复的数据库
            shutil.copy2(src, db_file)
            logger.info(f"已恢复数据库: {db_file}")
        
        # 恢复对话历史文件
        for dialogue_file in [f for f in os.listdir(tmp_dir) if f.startswith('dialogue_history_') and f.endswith('.json')]:
            src = os.path.join(tmp_dir, dialogue_file)
            shutil.copy2(src, dialogue_file)
            logger.info(f"已恢复对话历史: {dialogue_file}")
        
        # 恢复配置文件 (如果存在)
        if os.path.exists(os.path.join(tmp_dir, '.env')):
            # 如果当前存在.env，先备份
            if os.path.exists('.env'):
                backup_name = f".env.bak.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                shutil.copy2('.env', backup_name)
                logger.info(f"已备份现有.env: {backup_name}")
            shutil.copy2(os.path.join(tmp_dir, '.env'), '.env')
            logger.info("已恢复.env配置文件")
        
        logger.info("数据恢复完成")
        return True
        
    except Exception as e:
        logger.error(f"恢复过程中出错: {str(e)}")
        return False
    finally:
        # 清理临时目录
        shutil.rmtree(tmp_dir)

def download_from_cloud(config, backup_name, cloud_provider):
    """从云存储下载备份"""
    backup_dir = config['general']['backup_dir']
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    local_path = os.path.join(backup_dir, backup_name)
    
    if cloud_provider == "aws":
        try:
            import boto3
            
            if not config.getboolean('aws', 'enabled'):
                logger.error("AWS备份未启用")
                return None
                
            # 设置AWS凭证
            access_key = config['aws']['access_key']
            secret_key = config['aws']['secret_key']
            region = config['aws']['region']
            bucket = config['aws']['bucket']
            prefix = config['aws']['prefix']
            
            if not access_key or not secret_key:
                logger.error("AWS凭证未配置")
                return None
            
            # 创建S3客户端
            s3_client = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
            
            object_name = f"{prefix}{backup_name}"
            s3_client.download_file(bucket, object_name, local_path)
            logger.info(f"已从AWS S3下载备份: {local_path}")
            return local_path
            
        except ImportError:
            logger.error("未安装boto3库，无法从AWS S3下载。请运行 'pip install boto3'")
            return None
        except Exception as e:
            logger.error(f"从AWS S3下载失败: {e}")
            return None
            
    elif cloud_provider == "gcp":
        try:
            from google.cloud import storage
            
            if not config.getboolean('gcp', 'enabled'):
                logger.error("GCP备份未启用")
                return None
                
            # 设置GCP凭证
            credentials_file = config['gcp']['credentials_file']
            bucket_name = config['gcp']['bucket']
            prefix = config['gcp']['prefix']
            
            if credentials_file and os.path.exists(credentials_file):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_file
            
            # 创建Storage客户端
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            
            blob = bucket.blob(f"{prefix}{backup_name}")
            blob.download_to_filename(local_path)
            logger.info(f"已从Google Cloud Storage下载备份: {local_path}")
            return local_path
            
        except ImportError:
            logger.error("未安装google-cloud-storage库，无法从GCP下载。请运行 'pip install google-cloud-storage'")
            return None
        except Exception as e:
            logger.error(f"从Google Cloud Storage下载失败: {e}")
            return None
            
    elif cloud_provider == "azure":
        try:
            from azure.storage.blob import BlobServiceClient
            
            if not config.getboolean('azure', 'enabled'):
                logger.error("Azure备份未启用")
                return None
                
            # 设置Azure凭证
            connection_string = config['azure']['connection_string']
            container_name = config['azure']['container']
            prefix = config['azure']['prefix']
            
            if not connection_string:
                logger.error("Azure连接字符串未配置")
                return None
            
            # 创建Blob客户端
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            blob_client = blob_service_client.get_blob_client(
                container=container_name, 
                blob=f"{prefix}{backup_name}"
            )
            
            with open(local_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())
                
            logger.info(f"已从Azure Blob Storage下载备份: {local_path}")
            return local_path
            
        except ImportError:
            logger.error("未安装azure-storage-blob库，无法从Azure下载。请运行 'pip install azure-storage-blob'")
            return None
        except Exception as e:
            logger.error(f"从Azure Blob Storage下载失败: {e}")
            return None
    
    else:
        logger.error(f"不支持的云提供商: {cloud_provider}")
        return None

def list_cloud_backups(config, cloud_provider):
    """列出云存储中的备份"""
    if cloud_provider == "aws":
        try:
            import boto3
            
            if not config.getboolean('aws', 'enabled'):
                logger.error("AWS备份未启用")
                return []
                
            # 设置AWS凭证
            access_key = config['aws']['access_key']
            secret_key = config['aws']['secret_key']
            region = config['aws']['region']
            bucket = config['aws']['bucket']
            prefix = config['aws']['prefix']
            
            if not access_key or not secret_key:
                logger.error("AWS凭证未配置")
                return []
            
            # 创建S3客户端
            s3_client = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
            
            response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            backups = []
            
            if 'Contents' in response:
                for item in response['Contents']:
                    # 从完整路径中获取文件名部分
                    key = item['Key']
                    if key.startswith(prefix):
                        name = key[len(prefix):]
                        if name and (name.endswith('.tar.gz') or name.endswith('.zip')):
                            backups.append({
                                'name': name,
                                'size': item['Size'],
                                'last_modified': item['LastModified'].isoformat(),
                                'provider': 'aws'
                            })
            
            return backups
            
        except ImportError:
            logger.error("未安装boto3库，无法列出AWS S3备份。请运行 'pip install boto3'")
            return []
        except Exception as e:
            logger.error(f"列出AWS S3备份失败: {e}")
            return []
            
    elif cloud_provider == "gcp":
        try:
            from google.cloud import storage
            
            if not config.getboolean('gcp', 'enabled'):
                logger.error("GCP备份未启用")
                return []
                
            # 设置GCP凭证
            credentials_file = config['gcp']['credentials_file']
            bucket_name = config['gcp']['bucket']
            prefix = config['gcp']['prefix']
            
            if credentials_file and os.path.exists(credentials_file):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_file
            
            # 创建Storage客户端
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            
            blobs = bucket.list_blobs(prefix=prefix)
            backups = []
            
            for blob in blobs:
                name = blob.name[len(prefix):]
                if name and (name.endswith('.tar.gz') or name.endswith('.zip')):
                    backups.append({
                        'name': name,
                        'size': blob.size,
                        'last_modified': blob.updated.isoformat(),
                        'provider': 'gcp'
                    })
            
            return backups
            
        except ImportError:
            logger.error("未安装google-cloud-storage库，无法列出GCP备份。请运行 'pip install google-cloud-storage'")
            return []
        except Exception as e:
            logger.error(f"列出Google Cloud Storage备份失败: {e}")
            return []
            
    elif cloud_provider == "azure":
        try:
            from azure.storage.blob import BlobServiceClient
            
            if not config.getboolean('azure', 'enabled'):
                logger.error("Azure备份未启用")
                return []
                
            # 设置Azure凭证
            connection_string = config['azure']['connection_string']
            container_name = config['azure']['container']
            prefix = config['azure']['prefix']
            
            if not connection_string:
                logger.error("Azure连接字符串未配置")
                return []
            
            # 创建Blob客户端
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            container_client = blob_service_client.get_container_client(container_name)
            
            blobs = container_client.list_blobs(name_starts_with=prefix)
            backups = []
            
            for blob in blobs:
                name = blob.name[len(prefix):]
                if name and (name.endswith('.tar.gz') or name.endswith('.zip')):
                    backups.append({
                        'name': name,
                        'size': blob.size,
                        'last_modified': blob.last_modified.isoformat(),
                        'provider': 'azure'
                    })
            
            return backups
            
        except ImportError:
            logger.error("未安装azure-storage-blob库，无法列出Azure备份。请运行 'pip install azure-storage-blob'")
            return []
        except Exception as e:
            logger.error(f"列出Azure Blob Storage备份失败: {e}")
            return []
    
    else:
        logger.error(f"不支持的云提供商: {cloud_provider}")
        return []

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="RoundTable备份工具")
    subparsers = parser.add_subparsers(dest="command", help="要执行的命令")
    
    # 配置命令
    config_parser = subparsers.add_parser("config", help="配置备份设置")
    
    # 创建备份命令
    create_parser = subparsers.add_parser("create", help="创建新备份")
    create_parser.add_argument("--no-upload", action="store_true", help="不上传到云存储")
    
    # 恢复备份命令
    restore_parser = subparsers.add_parser("restore", help="从备份恢复")
    restore_parser.add_argument("file", help="要恢复的备份文件")
    
    # 列出本地备份命令
    list_local_parser = subparsers.add_parser("list-local", help="列出本地备份")
    
    # 列出云备份命令
    list_cloud_parser = subparsers.add_parser("list-cloud", help="列出云存储备份")
    list_cloud_parser.add_argument("--provider", choices=["aws", "gcp", "azure"], 
                                   required=True, help="云提供商")
    
    # 下载云备份命令
    download_parser = subparsers.add_parser("download", help="从云存储下载备份")
    download_parser.add_argument("--provider", choices=["aws", "gcp", "azure"], 
                                required=True, help="云提供商")
    download_parser.add_argument("file", help="要下载的备份文件名")
    
    # 调度命令
    schedule_parser = subparsers.add_parser("schedule", help="创建调度脚本")
    
    # 解析参数
    args = parser.parse_args()
    
    # 加载配置
    config = load_config()
    
    # 执行命令
    if args.command == "config":
        print("编辑配置文件:", CONFIG_FILE)
        print("请使用文本编辑器打开并修改该文件")
        
    elif args.command == "create":
        print("创建新备份...")
        archive_path = create_backup_archive(config)
        
        if not archive_path:
            print("创建备份失败")
            return
            
        if not args.no_upload:
            # 上传到所有已启用的云存储
            if config.getboolean('aws', 'enabled'):
                upload_to_aws(config, archive_path)
            
            if config.getboolean('gcp', 'enabled'):
                upload_to_gcp(config, archive_path)
            
            if config.getboolean('azure', 'enabled'):
                upload_to_azure(config, archive_path)
        
        # 清理旧备份
        clean_old_backups(config)
        
    elif args.command == "restore":
        print(f"从备份恢复: {args.file}")
        if restore_backup(args.file):
            print("恢复成功")
        else:
            print("恢复失败")
            
    elif args.command == "list-local":
        backup_dir = config['general']['backup_dir']
        if not os.path.exists(backup_dir):
            print("备份目录不存在")
            return
            
        backups = []
        for filename in os.listdir(backup_dir):
            if (filename.startswith("roundtable_v") and 
                (filename.endswith(".tar.gz") or filename.endswith(".zip"))):
                file_path = os.path.join(backup_dir, filename)
                backups.append({
                    'name': filename,
                    'size': os.path.getsize(file_path),
                    'last_modified': datetime.datetime.fromtimestamp(
                        os.path.getmtime(file_path)).isoformat()
                })
        
        # 按修改时间排序
        backups.sort(key=lambda x: x['last_modified'], reverse=True)
        
        if not backups:
            print("没有找到本地备份")
        else:
            print("本地备份:")
            for i, backup in enumerate(backups, 1):
                size_mb = backup['size'] / (1024 * 1024)
                print(f"{i}. {backup['name']} ({size_mb:.2f} MB) - {backup['last_modified']}")
            
    elif args.command == "list-cloud":
        backups = list_cloud_backups(config, args.provider)
        
        if not backups:
            print(f"没有在{args.provider}找到云备份")
        else:
            print(f"{args.provider}云备份:")
            for i, backup in enumerate(backups, 1):
                size_mb = backup['size'] / (1024 * 1024)
                print(f"{i}. {backup['name']} ({size_mb:.2f} MB) - {backup['last_modified']}")
            
    elif args.command == "download":
        print(f"从{args.provider}下载备份: {args.file}")
        local_path = download_from_cloud(config, args.file, args.provider)
        if local_path:
            print(f"下载成功: {local_path}")
        else:
            print("下载失败")
            
    elif args.command == "schedule":
        create_schedule_script()
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 