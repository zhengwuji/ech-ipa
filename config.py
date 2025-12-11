import os
import yaml
from typing import Any, Dict


CONFIG_PATH = "config.yaml"


def desktop_default_folder() -> str:
    return os.path.join(os.path.expanduser("~"), "Desktop", "jianche1")


def default_paths() -> Dict[str, str]:
    base = desktop_default_folder()
    return {
        "save_path": base,
        "screenshot_path": os.path.join(base, "screenshots"),
        "data_path": os.path.join(base, "saved_data"),
    }


def default_config() -> Dict[str, Any]:
    paths = default_paths()
    return {
        "target_url": "",
        "check_interval": 60,
        "save_path": paths["save_path"],
        "screenshot_path": paths["screenshot_path"],
        "data_path": paths["data_path"],
        "hotkey": "F9",
        "region": None,  # {"x_ratio": 0, "y_ratio": 0, "w_ratio": 0, "h_ratio": 0, "ref_width": 0, "ref_height": 0}
        "last_text": "",
    }


def ensure_directories(conf: Dict[str, Any]) -> None:
    os.makedirs(conf.get("save_path", ""), exist_ok=True)
    os.makedirs(conf.get("screenshot_path", ""), exist_ok=True)
    os.makedirs(conf.get("data_path", ""), exist_ok=True)


def load_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_PATH):
        conf = default_config()
        ensure_directories(conf)
        save_config(conf)
        return conf
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f) or {}
    merged = default_config()
    merged.update(conf)
    ensure_directories(merged)
    return merged


def save_config(conf: Dict[str, Any]) -> None:
    ensure_directories(conf)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(conf, f, allow_unicode=True, sort_keys=False)

