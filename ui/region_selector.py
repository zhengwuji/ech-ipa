# 区域选择器窗口
import sys
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QLineEdit, QSpinBox, QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
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
        """打开浏览器选择区域"""
        try:
            # 使用Selenium打开浏览器（非无头模式）让用户选择
            chrome_options = Options()
            # 不使用无头模式，让用户可以看到并交互
            chrome_options.add_argument('--window-size=1920,1080')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.get(self.url)
            
            QMessageBox.information(self, "提示", 
                "浏览器已打开，请在页面中查看元素位置，然后在本窗口输入坐标。\n\n"
                "提示：可以使用浏览器开发者工具(F12)查看元素的坐标和尺寸。")
        
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开浏览器: {str(e)}")
    
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

