# 浏览器检测模块
import os
import platform
import winreg
from pathlib import Path

def get_default_browser():
    """获取系统默认浏览器路径"""
    try:
        # 读取注册表获取默认浏览器
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                           r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice") as key:
            prog_id = winreg.QueryValueEx(key, "ProgId")[0]
        
        # 根据ProgId查找浏览器路径
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{prog_id}\shell\open\command") as key:
                command = winreg.QueryValueEx(key, "")[0]
                # 移除引号和参数
                browser_path = command.split('"')[1] if '"' in command else command.split()[0]
                # 清理路径中的转义字符
                browser_path = browser_path.replace('\\', os.sep).replace('"', '')
                if os.path.exists(browser_path):
                    return browser_path
        except:
            # 如果直接查找失败，尝试常见的浏览器路径
            pass
    except:
        pass
    return None

def find_chrome():
    """查找Chrome浏览器路径"""
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
        r"C:\Users\Public\Desktop\Google Chrome.lnk",  # 快捷方式
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            # 如果是快捷方式，尝试解析
            if path.endswith('.lnk'):
                try:
                    import win32com.client
                    shell = win32com.client.Dispatch("WScript.Shell")
                    shortcut = shell.CreateShortCut(path)
                    if os.path.exists(shortcut.Targetpath):
                        return shortcut.Targetpath
                except:
                    pass
            else:
                return path
    
    return None

def find_edge():
    """查找Edge浏览器路径"""
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe"),
    ]
    
    for path in edge_paths:
        if os.path.exists(path):
            return path
    
    return None

def find_firefox():
    """查找Firefox浏览器路径"""
    firefox_paths = [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        os.path.expanduser(r"~\AppData\Local\Mozilla Firefox\firefox.exe"),
    ]
    
    for path in firefox_paths:
        if os.path.exists(path):
            return path
    
    return None

def detect_browsers():
    """检测所有已安装的浏览器"""
    browsers = {}
    
    # 检测默认浏览器
    default = get_default_browser()
    if default:
        browsers['default'] = default
        # 判断默认浏览器类型
        if 'chrome' in default.lower():
            browsers['chrome'] = default
        elif 'edge' in default.lower() or 'msedge' in default.lower():
            browsers['edge'] = default
        elif 'firefox' in default.lower():
            browsers['firefox'] = default
    
    # 检测Chrome
    chrome = find_chrome()
    if chrome and chrome not in browsers.values():
        browsers['chrome'] = chrome
    
    # 检测Edge
    edge = find_edge()
    if edge and edge not in browsers.values():
        browsers['edge'] = edge
    
    # 检测Firefox
    firefox = find_firefox()
    if firefox and firefox not in browsers.values():
        browsers['firefox'] = firefox
    
    return browsers

def get_browser_name(path):
    """根据路径判断浏览器名称"""
    if not path:
        return None
    
    path_lower = path.lower()
    if 'chrome' in path_lower:
        return 'chrome'
    elif 'edge' in path_lower or 'msedge' in path_lower:
        return 'edge'
    elif 'firefox' in path_lower:
        return 'firefox'
    else:
        return 'unknown'

def get_browser_driver_name(browser_name):
    """获取浏览器对应的驱动名称"""
    driver_map = {
        'chrome': 'chromedriver',
        'edge': 'msedgedriver',
        'firefox': 'geckodriver'
    }
    return driver_map.get(browser_name, 'chromedriver')

