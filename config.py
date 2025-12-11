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
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if config is None:
                    config = {}
                # 合并默认配置
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        return DEFAULT_CONFIG.copy()
    except Exception as e:
        print(f"加载配置失败: {e}，使用默认配置")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """保存配置"""
    try:
        # 确保目录存在
        config_dir = os.path.dirname(CONFIG_FILE) if os.path.dirname(CONFIG_FILE) else '.'
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    except Exception as e:
        print(f"保存配置失败: {e}")
        raise

def ensure_directories(config):
    """确保所有必要的目录存在"""
    try:
        if config.get('save_path'):
            os.makedirs(config['save_path'], exist_ok=True)
        if config.get('screenshot_path'):
            os.makedirs(config['screenshot_path'], exist_ok=True)
        if config.get('data_path'):
            os.makedirs(config['data_path'], exist_ok=True)
    except Exception as e:
        print(f"创建目录失败: {e}")
        raise

