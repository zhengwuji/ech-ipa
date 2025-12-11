# 区域选择器窗口
import sys
import os

# 确保可以导入上级目录的模块
if getattr(sys, 'frozen', False):
    # 打包后的exe模式
    base_path = sys._MEIPASS
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    if base_path not in sys.path:
        sys.path.insert(0, base_path)
else:
    # 开发模式
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QLineEdit, QSpinBox, QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# 导入browser_detector
try:
    from browser_detector import detect_browsers, get_browser_name
except ImportError:
    try:
        if getattr(sys, 'frozen', False):
            import importlib
            browser_detector = importlib.import_module('browser_detector')
            detect_browsers = browser_detector.detect_browsers
            get_browser_name = browser_detector.get_browser_name
        else:
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            import importlib.util
            spec = importlib.util.spec_from_file_location("browser_detector", os.path.join(parent_dir, "browser_detector.py"))
            browser_detector = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(browser_detector)
            detect_browsers = browser_detector.detect_browsers
            get_browser_name = browser_detector.get_browser_name
    except Exception as e:
        raise ImportError(f"无法导入 browser_detector: {e}")

from PIL import Image
import io
import time

class RegionSelector(QDialog):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.region = None
        self.driver = None
        self.init_ui()
        self.load_page_screenshot()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("选择监控区域")
        self.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout(self)
        
        # 说明
        info_label = QLabel("在打开的浏览器窗口中，使用鼠标拖拽选择要监控的区域")
        layout.addWidget(info_label)
        
        # 坐标输入
        coord_group = QGroupBox("区域坐标")
        coord_layout = QVBoxLayout()
        
        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("X坐标:"))
        self.x_spin = QSpinBox()
        self.x_spin.setMinimum(0)
        self.x_spin.setMaximum(9999)
        x_layout.addWidget(self.x_spin)
        coord_layout.addLayout(x_layout)
        
        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Y坐标:"))
        self.y_spin = QSpinBox()
        self.y_spin.setMinimum(0)
        self.y_spin.setMaximum(9999)
        y_layout.addWidget(self.y_spin)
        coord_layout.addLayout(y_layout)
        
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("宽度:"))
        self.width_spin = QSpinBox()
        self.width_spin.setMinimum(1)
        self.width_spin.setMaximum(9999)
        self.width_spin.setValue(200)
        width_layout.addWidget(self.width_spin)
        coord_layout.addLayout(width_layout)
        
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("高度:"))
        self.height_spin = QSpinBox()
        self.height_spin.setMinimum(1)
        self.height_spin.setMaximum(9999)
        self.height_spin.setValue(200)
        height_layout.addWidget(self.height_spin)
        coord_layout.addLayout(height_layout)
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("区域名称:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("价格区域/销售量区域/评价区域等")
        name_layout.addWidget(self.name_input)
        coord_layout.addLayout(name_layout)
        
        coord_group.setLayout(coord_layout)
        layout.addWidget(coord_group)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        self.open_browser_btn = QPushButton("打开浏览器选择区域")
        self.open_browser_btn.clicked.connect(self.open_browser_selector)
        btn_layout.addWidget(self.open_browser_btn)
        
        btn_layout.addStretch()
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept_region)
        btn_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def load_page_screenshot(self):
        """加载页面截图用于预览"""
        # 这个功能可以后续扩展
        pass
    
    def open_browser_selector(self):
        """打开浏览器选择区域 - 自动使用系统默认浏览器"""
        try:
            import os
            import shutil
            
            # 检测已安装的浏览器
            browsers = detect_browsers()
            
            if not browsers:
                QMessageBox.warning(self, "错误", 
                    "未找到已安装的浏览器！\n\n"
                    "请安装以下浏览器之一：\n"
                    "1. Google Chrome\n"
                    "2. Microsoft Edge")
                return
            
            # 优先使用默认浏览器
            browser_path = None
            browser_type = None
            
            if 'default' in browsers:
                browser_path = browsers['default']
                browser_type = get_browser_name(browser_path)
            elif 'chrome' in browsers:
                browser_path = browsers['chrome']
                browser_type = 'chrome'
            elif 'edge' in browsers:
                browser_path = browsers['edge']
                browser_type = 'edge'
            else:
                browser_path = list(browsers.values())[0]
                browser_type = get_browser_name(browser_path)
            
            # 根据浏览器类型设置选项
            if browser_type == 'edge' or (browser_type == 'unknown' and 'edge' in browser_path.lower()):
                options = EdgeOptions()
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                options.binary_location = browser_path
                
                try:
                    cache_path = os.path.join(os.path.expanduser("~"), ".wdm")
                    driver_path = EdgeChromiumDriverManager().install()
                    
                    if os.path.exists(driver_path):
                        file_size = os.path.getsize(driver_path)
                        if file_size < 100 * 1024:
                            if os.path.exists(cache_path):
                                shutil.rmtree(cache_path, ignore_errors=True)
                            driver_path = EdgeChromiumDriverManager().install()
                    
                    service = EdgeService(driver_path)
                    self.driver = webdriver.Edge(service=service, options=options)
                    self.driver.get(self.url)
                    
                    QMessageBox.information(self, "提示", 
                        f"已使用 {browser_type} 浏览器打开页面\n\n"
                        "请在页面中查看元素位置，然后在本窗口输入坐标。\n\n"
                        "提示：可以使用浏览器开发者工具(F12)查看元素的坐标和尺寸。")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"打开Edge浏览器失败: {str(e)}")
            else:
                # Chrome或基于Chromium的浏览器
                options = ChromeOptions()
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                options.binary_location = browser_path
                
                try:
                    cache_path = os.path.join(os.path.expanduser("~"), ".wdm")
                    driver_path = ChromeDriverManager().install()
                    
                    if os.path.exists(driver_path):
                        file_size = os.path.getsize(driver_path)
                        if file_size < 100 * 1024:
                            if os.path.exists(cache_path):
                                shutil.rmtree(cache_path, ignore_errors=True)
                            driver_path = ChromeDriverManager().install()
                    
                    service = ChromeService(driver_path)
                    self.driver = webdriver.Chrome(service=service, options=options)
                    self.driver.get(self.url)
                    
                    QMessageBox.information(self, "提示", 
                        f"已使用 {browser_type} 浏览器打开页面\n\n"
                        "请在页面中查看元素位置，然后在本窗口输入坐标。\n\n"
                        "提示：可以使用浏览器开发者工具(F12)查看元素的坐标和尺寸。")
                except Exception as driver_error:
                    error_msg = str(driver_error)
                    
                    if "WinError 193" in error_msg or "不是有效的Win32" in error_msg:
                        try:
                            cache_path = os.path.join(os.path.expanduser("~"), ".wdm")
                            if os.path.exists(cache_path):
                                shutil.rmtree(cache_path, ignore_errors=True)
                                QMessageBox.information(self, "提示", 
                                    "已清除驱动缓存，正在重新下载...")
                            driver_path = ChromeDriverManager().install()
                            service = ChromeService(driver_path)
                            self.driver = webdriver.Chrome(service=service, options=options)
                            self.driver.get(self.url)
                            
                            QMessageBox.information(self, "提示", 
                                "浏览器已打开，请在页面中查看元素位置，然后在本窗口输入坐标。")
                        except Exception as retry_error:
                            QMessageBox.critical(self, "错误", 
                                f"无法打开浏览器 (WinError 193): {str(retry_error)}\n\n"
                                f"请运行 '清理驱动缓存.bat' 后再试")
                    else:
                        QMessageBox.warning(self, "错误", 
                            f"无法打开浏览器: {error_msg}\n\n"
                            f"请确保：\n"
                            f"1. 浏览器已安装\n"
                            f"2. 网络连接正常")
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开浏览器时发生错误: {str(e)}")
    
    def accept_region(self):
        """确认区域"""
        if not self.name_input.text():
            QMessageBox.warning(self, "提示", "请输入区域名称")
            return
        
        self.region = {
            'name': self.name_input.text(),
            'x': self.x_spin.value(),
            'y': self.y_spin.value(),
            'width': self.width_spin.value(),
            'height': self.height_spin.value()
        }
        
        if self.driver:
            self.driver.quit()
        
        self.accept()
    
    def get_region(self):
        """获取选择的区域"""
        return self.region
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.driver:
            self.driver.quit()
        event.accept()

