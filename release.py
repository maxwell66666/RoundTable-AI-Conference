#!/usr/bin/env python3
"""
版本发布脚本
处理版本号更新、数据库迁移和发布过程
"""

import os
import re
import sys
import json
import argparse
import subprocess
from datetime import datetime

# 脚本路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(SCRIPT_DIR, "version.py")

def get_current_version():
    """从version.py文件获取当前版本"""
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
        if match:
            return match.group(1)
    return "0.0.0"

def update_version_file(new_version, build_date=None, changelog_entry=None):
    """更新version.py文件中的版本号"""
    if build_date is None:
        build_date = datetime.now().strftime("%Y%m%d")
    
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 更新版本号
    content = re.sub(r'__version__\s*=\s*"([^"]+)"', f'__version__ = "{new_version}"', content)
    
    # 更新构建日期
    content = re.sub(r'__build__\s*=\s*"([^"]+)"', f'__build__ = "{build_date}"', content)
    
    # 如果需要，更新变更日志
    if f'"{new_version}"' not in content:
        # 找到变更日志字典
        changelog_match = re.search(r'("changelog"\s*:\s*{)(.*?)(})', content, re.DOTALL)
        if changelog_match:
            changelog_start = changelog_match.group(1)
            changelog_content = changelog_match.group(2)
            changelog_end = changelog_match.group(3)
            
            # 添加新版本的变更日志条目
            if changelog_entry:
                # 使用提供的变更日志条目
                changelog_items = '",\n            "'.join(changelog_entry)
                new_entry = f'\n        "{new_version}": [\n            "{changelog_items}"\n        ],'
            else:
                # 使用默认变更日志条目
                new_entry = f'\n        "{new_version}": [\n            "版本 {new_version} 更新"\n        ],'
            
            updated_changelog = changelog_start + new_entry + changelog_content + changelog_end
            content = content.replace(changelog_match.group(0), updated_changelog)
    
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"版本文件已更新: {new_version} (构建 {build_date})")

def bump_version(current_version, bump_type):
    """增加版本号"""
    major, minor, patch = map(int, current_version.split('.'))
    
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        return current_version

def run_migrations():
    """运行数据库迁移"""
    try:
        subprocess.run([sys.executable, "db_migrations.py"], check=True)
        print("数据库迁移成功")
        return True
    except subprocess.CalledProcessError:
        print("数据库迁移失败")
        return False

def create_backup():
    """创建系统备份"""
    if not os.path.exists("backup.py"):
        print("备份模块不存在，跳过备份步骤")
        return True
    
    try:
        print("正在创建系统备份...")
        result = subprocess.run([sys.executable, "backup.py", "create"], check=True)
        print("系统备份成功")
        return True
    except subprocess.CalledProcessError:
        print("系统备份失败，但继续执行发布流程")
        return True  # 失败时仍然返回True，因为备份失败不应该阻止整个发布流程

def update_requirements():
    """更新requirements.txt以包含备份所需的依赖"""
    req_file = "requirements.txt"
    
    # 备份相关依赖
    backup_deps = [
        "# 备份系统依赖",
        "# 取消下方注释以启用对应云存储支持",
        "# boto3>=1.26.0  # AWS S3支持",
        "# google-cloud-storage>=2.7.0  # Google Cloud Storage支持",
        "# azure-storage-blob>=12.14.0  # Azure Blob Storage支持"
    ]
    
    if os.path.exists(req_file):
        with open(req_file, "r", encoding="utf-8") as f:
            requirements = f.read()
        
        # 检查是否已添加备份依赖
        if "# 备份系统依赖" not in requirements:
            with open(req_file, "a", encoding="utf-8") as f:
                f.write("\n\n# 备份系统依赖\n")
                f.write("\n".join(backup_deps[1:]))
            print("已更新requirements.txt文件，添加备份系统依赖")
        else:
            print("requirements.txt已包含备份系统依赖")
    else:
        print("requirements.txt文件不存在")

def generate_changelog(prev_version, new_version):
    """生成自上一版本以来的变更日志"""
    try:
        # 获取git提交日志
        cmd = ["git", "log", f"v{prev_version}..HEAD", "--pretty=format:%s"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        commits = result.stdout.strip().split("\n")
        
        # 过滤有效的提交信息
        changelog_entries = []
        for commit in commits:
            # 忽略合并提交和空提交
            if commit and not commit.startswith("Merge"):
                # 清理提交信息
                entry = commit.strip()
                # 如果消息太长，截断它
                if len(entry) > 80:
                    entry = entry[:77] + "..."
                changelog_entries.append(entry)
        
        # 如果没有有效条目，添加默认条目
        if not changelog_entries:
            changelog_entries = [f"版本从 {prev_version} 更新到 {new_version}"]
            
        return changelog_entries
        
    except subprocess.CalledProcessError:
        # Git命令失败，返回默认变更日志
        return [f"版本从 {prev_version} 更新到 {new_version}"]
    except FileNotFoundError:
        # Git可能不可用
        return [f"版本从 {prev_version} 更新到 {new_version}"]

def create_release_archive(version):
    """创建发布归档文件"""
    release_dir = "releases"
    if not os.path.exists(release_dir):
        os.makedirs(release_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"roundtable_v{version}_{timestamp}"
    
    # 创建要排除的文件列表
    exclude_patterns = [
        "__pycache__", "*.pyc", "*.pyo", "*.pyd", 
        ".git", ".gitignore", ".env", "*.db", "*.sqlite3",
        "env", "venv", "*.log", "dialogue_history_*",
        "releases", "*.zip", "*.tar.gz", "backups"
    ]
    
    exclude_args = []
    for pattern in exclude_patterns:
        exclude_args.extend(["--exclude", pattern])
    
    try:
        # 创建tar归档
        tar_filename = os.path.join(release_dir, f"{archive_name}.tar.gz")
        subprocess.run(["tar", "-czf", tar_filename, "--exclude-vcs"] + exclude_args + ["."], check=True)
        print(f"已创建发布归档: {tar_filename}")
        return tar_filename
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("创建tar归档失败，尝试创建zip归档")
        try:
            # 如果tar失败，尝试使用zip
            zip_filename = os.path.join(release_dir, f"{archive_name}.zip")
            
            # 在Windows上可能需要使用不同的命令
            if os.name == "nt":
                # Windows可以使用内置的zipfile模块
                import zipfile
                import glob
                
                def should_exclude(file_path):
                    """检查文件是否应该被排除"""
                    from fnmatch import fnmatch
                    for pattern in exclude_patterns:
                        if fnmatch(file_path, pattern) or any(fnmatch(part, pattern) for part in file_path.split(os.sep)):
                            return True
                    return False
                
                with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk('.'):
                        # 排除不需要的目录
                        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]
                        
                        for file in files:
                            file_path = os.path.join(root, file)
                            if not should_exclude(file_path):
                                zipf.write(file_path)
            else:
                # 在Unix系统上使用zip命令
                subprocess.run(["zip", "-r", zip_filename, "."] + 
                              [f"-x {pattern}" for pattern in exclude_patterns], check=True)
            
            print(f"已创建发布归档: {zip_filename}")
            return zip_filename
        except Exception as e:
            print(f"创建归档失败: {str(e)}")
            return None

def main():
    parser = argparse.ArgumentParser(description="版本发布工具")
    parser.add_argument("command", choices=["bump", "release", "migrate", "backup"], help="要执行的命令")
    parser.add_argument("--type", choices=["major", "minor", "patch"], default="patch", help="版本更新类型")
    parser.add_argument("--version", help="指定特定版本号")
    parser.add_argument("--auto-changelog", action="store_true", help="自动生成变更日志")
    parser.add_argument("--skip-backup", action="store_true", help="跳过备份步骤")
    args = parser.parse_args()
    
    current_version = get_current_version()
    print(f"当前版本: {current_version}")
    
    if args.command == "bump":
        if args.version:
            new_version = args.version
        else:
            new_version = bump_version(current_version, args.type)
        
        # 生成变更日志
        changelog_entry = None
        if args.auto_changelog:
            changelog_entry = generate_changelog(current_version, new_version)
        
        update_version_file(new_version, changelog_entry=changelog_entry)
        print(f"版本已更新为: {new_version}")
        
        # 检查是否需要更新requirements.txt
        update_requirements()
    
    elif args.command == "migrate":
        success = run_migrations()
        if not success:
            sys.exit(1)
        print("数据库迁移完成")
    
    elif args.command == "backup":
        success = create_backup()
        if not success:
            print("备份失败")
            sys.exit(1)
        print("备份完成")
    
    elif args.command == "release":
        # 创建备份
        if not args.skip_backup:
            print("开始创建系统备份...")
            create_backup()
        else:
            print("跳过备份步骤")
        
        # 更新版本号
        if args.version:
            new_version = args.version
        else:
            new_version = bump_version(current_version, args.type)
        
        # 生成变更日志
        changelog_entry = None
        if args.auto_changelog:
            changelog_entry = generate_changelog(current_version, new_version)
        
        update_version_file(new_version, changelog_entry=changelog_entry)
        print(f"版本已更新为: {new_version}")
        
        # 检查是否需要更新requirements.txt
        update_requirements()
        
        # 运行迁移
        print("开始执行数据库迁移...")
        success = run_migrations()
        if not success:
            print("由于迁移失败，发布过程中止")
            sys.exit(1)
        
        # 创建发布归档
        print("开始创建发布归档...")
        archive_path = create_release_archive(new_version)
        if archive_path:
            print(f"成功创建版本 {new_version} 的发布归档")
            print(f"归档文件: {archive_path}")
        else:
            print("创建发布归档失败")
            sys.exit(1)

if __name__ == "__main__":
    main() 