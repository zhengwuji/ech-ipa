# 配置管理模块
import os
import yaml
from pathlib import Path

CONFIG_FILE = "config.yaml"
DEFAULT_CONFIG = {
    'save_path': str(Path.home() / 'Desktop' / 'jianche1'),
    'screenshot_path': str(Path.home() / 'Desktop' / 'jianche1' / 'screenshots'),
    'data_path': str(Path.home() / 'Desktop' / 'jianche1' / 'saved_data'),
    'check_interval': 60,  # 秒，最小60秒
    'target_url': '',
    'monitor_regions': [],  # 监控区域 [{x, y, width, height, name}]
    'last_data': {}  # 上次的数据
}

def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            # 合并默认配置
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """保存配置"""
    # 确保目录存在
    os.makedirs(os.path.dirname(CONFIG_FILE) if os.path.dirname(CONFIG_FILE) else '.', exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

def ensure_directories(config):
    """确保所有必要的目录存在"""
    os.makedirs(config['save_path'], exist_ok=True)
    os.makedirs(config['screenshot_path'], exist_ok=True)
    os.makedirs(config['data_path'], exist_ok=True)

