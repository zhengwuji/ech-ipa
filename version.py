# 版本管理模块
import os
import json

VERSION_FILE = "version.json"

def get_version():
    """获取当前版本号"""
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('version', '1.0.00')
    return '1.0.00'

def increment_version():
    """递增版本号 1.0.00 -> 1.0.01 -> ... -> 9.9.99 -> 1.0.00"""
    current = get_version()
    parts = current.split('.')
    major = int(parts[0])
    minor = int(parts[1])
    patch = int(parts[2])
    
    patch += 1
    if patch > 99:
        patch = 0
        minor += 1
        if minor > 9:
            minor = 0
            major += 1
            if major > 9:
                major = 1
    
    new_version = f"{major}.{minor}.{patch:02d}"
    
    with open(VERSION_FILE, 'w', encoding='utf-8') as f:
        json.dump({'version': new_version}, f, ensure_ascii=False, indent=2)
    
    return new_version

def set_version(version):
    """设置版本号"""
    with open(VERSION_FILE, 'w', encoding='utf-8') as f:
        json.dump({'version': version}, f, ensure_ascii=False, indent=2)

