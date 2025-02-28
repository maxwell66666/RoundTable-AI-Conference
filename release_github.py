#!/usr/bin/env python3
"""
GitHub发布脚本
用于创建GitHub版本发布和标签
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime
import json
import requests

def get_current_version():
    """从version.py文件获取当前版本"""
    with open("version.py", "r", encoding="utf-8") as f:
        content = f.read()
        import re
        match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
        if match:
            return match.group(1)
    return "0.0.0"

def get_github_repo():
    """获取GitHub仓库信息"""
    try:
        remote_url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"], 
            universal_newlines=True
        ).strip()
        
        # 处理不同格式的URL
        if remote_url.startswith("https://github.com/"):
            parts = remote_url.replace("https://github.com/", "").replace(".git", "").split("/")
        elif remote_url.startswith("git@github.com:"):
            parts = remote_url.replace("git@github.com:", "").replace(".git", "").split("/")
        else:
            return None, None
            
        if len(parts) >= 2:
            return parts[0], parts[1]  # 所有者和仓库名
        return None, None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, None

def create_github_release(version, token, prerelease=False, draft=False):
    """创建GitHub版本发布"""
    owner, repo = get_github_repo()
    if not owner or not repo:
        print("无法确定GitHub仓库信息。请确保这是一个有效的GitHub仓库。")
        return False
    
    # 获取变更日志
    changelog = get_changelog_for_version(version)
    
    # 准备发布数据
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    
    # 检查标签是否已存在，如果不存在则创建
    tag_name = f"v{version}"
    try:
        # 创建标签
        subprocess.run(["git", "tag", "-a", tag_name, "-m", f"版本 {version}"], check=True)
        subprocess.run(["git", "push", "origin", tag_name], check=True)
        print(f"已创建并推送标签: {tag_name}")
    except subprocess.CalledProcessError:
        print(f"标签 {tag_name} 可能已存在或无法创建")
    
    # 创建发布
    data = {
        "tag_name": tag_name,
        "target_commitish": "master",  # 或根据您的分支策略调整
        "name": f"版本 {version}",
        "body": changelog,
        "draft": draft,
        "prerelease": prerelease
    }
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 201:
        release_info = response.json()
        print(f"GitHub发布创建成功: {release_info['html_url']}")
        
        # 上传发布资产
        upload_release_assets(release_info["upload_url"].split("{")[0], token, version)
        return True
    else:
        print(f"创建GitHub发布失败: {response.status_code}")
        print(response.text)
        return False

def upload_release_assets(upload_url, token, version):
    """上传发布资产到GitHub发布"""
    # 查找发布文件
    release_dir = "releases"
    if not os.path.exists(release_dir):
        print(f"发布目录 {release_dir} 不存在")
        return
    
    # 查找与版本匹配的发布文件
    release_files = [f for f in os.listdir(release_dir) 
                     if f.startswith(f"roundtable_v{version}_") and 
                     (f.endswith(".tar.gz") or f.endswith(".zip"))]
    
    if not release_files:
        print(f"未找到版本 {version} 的发布文件")
        
        # 尝试创建发布归档
        print("尝试创建发布归档...")
        try:
            subprocess.run([sys.executable, "release.py", "release", "--version", version, "--skip-backup"], check=True)
            
            # 重新查找发布文件
            release_files = [f for f in os.listdir(release_dir) 
                            if f.startswith(f"roundtable_v{version}_") and 
                            (f.endswith(".tar.gz") or f.endswith(".zip"))]
        except:
            print("创建发布归档失败")
    
    # 上传每个发布文件
    for file_name in release_files:
        file_path = os.path.join(release_dir, file_name)
        
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/octet-stream"
        }
        
        with open(file_path, "rb") as f:
            file_data = f.read()
            
        asset_url = f"{upload_url}?name={file_name}"
        response = requests.post(asset_url, headers=headers, data=file_data)
        
        if response.status_code == 201:
            print(f"上传资产成功: {file_name}")
        else:
            print(f"上传资产失败: {file_name}, 状态码: {response.status_code}")
            print(response.text)

def get_changelog_for_version(version):
    """从version.py中获取指定版本的变更日志"""
    try:
        with open("version.py", "r", encoding="utf-8") as f:
            content = f.read()
            
        import re
        changelog_match = re.search(r'"changelog"\s*:\s*{(.*?)}', content, re.DOTALL)
        if changelog_match:
            changelog_content = changelog_match.group(1)
            version_match = re.search(rf'"{version}"\s*:\s*\[(.*?)\]', changelog_content, re.DOTALL)
            
            if version_match:
                items = version_match.group(1).strip()
                # 解析项目列表
                changelog_items = [item.strip(' \t\n"\'') for item in items.split('",')]
                # 格式化为markdown列表
                return "## 变更内容\n\n" + "\n".join([f"* {item}" for item in changelog_items if item])
    except Exception as e:
        print(f"获取变更日志时出错: {str(e)}")
    
    # 如果无法获取变更日志，则返回默认信息
    return f"## 版本 {version}\n\n* 查看代码提交历史获取详细变更"

def main():
    parser = argparse.ArgumentParser(description="GitHub发布工具")
    parser.add_argument("--version", help="要发布的版本号 (默认使用version.py中的当前版本)")
    parser.add_argument("--token", help="GitHub API令牌")
    parser.add_argument("--prerelease", action="store_true", help="标记为预发布版本")
    parser.add_argument("--draft", action="store_true", help="创建为草稿版本")
    args = parser.parse_args()
    
    # 确定版本
    version = args.version if args.version else get_current_version()
    print(f"准备发布版本: {version}")
    
    # 获取GitHub令牌
    token = args.token
    if not token:
        token = os.environ.get("GITHUB_TOKEN")
    
    if not token:
        print("错误: 必须提供GitHub API令牌")
        print("请使用--token参数或设置GITHUB_TOKEN环境变量")
        return 1
    
    # 创建GitHub发布
    success = create_github_release(
        version=version,
        token=token,
        prerelease=args.prerelease,
        draft=args.draft
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 