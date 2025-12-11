# 主窗口UI
import sys
import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QSpinBox,
                             QTextEdit, QFileDialog, QMessageBox, QGroupBox,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QDateTimeEdit, QScrollArea, QFrame)
from PyQt5.QtCore import Qt, QTimer, QDateTime, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QFont
import config
from web_monitor import WebMonitor
from datetime import datetime
import json
import shutil

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            self.config = config.load_config()
            try:
                config.ensure_directories(self.config)
            except Exception as e:
                print(f"创建目录时出错: {e}")
            
            self.monitor = None
            self.monitoring = False
            self.timer = QTimer()
            self.timer.timeout.connect(self.check_changes)
            
            self.init_ui()
            self.load_config_to_ui()
        except Exception as e:
            import traceback
            error_msg = f"初始化程序时出错:\n{str(e)}\n\n详细信息:\n{traceback.format_exc()}"
            QMessageBox.critical(None, "严重错误", error_msg)
            print(error_msg)
            raise
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("网站监控工具 - 实时检测销售量和价格")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 顶部设置区域
        settings_group = QGroupBox("设置")
        settings_layout = QVBoxLayout()
        
        # URL输入
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("监控网址:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入要监控的网站URL")
        url_layout.addWidget(self.url_input)
        settings_layout.addLayout(url_layout)
        
        # 保存路径
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("保存路径:"))
        self.save_path_input = QLineEdit()
        self.save_path_input.setReadOnly(True)
        path_layout.addWidget(self.save_path_input)
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.clicked.connect(self.browse_save_path)
        path_layout.addWidget(self.browse_btn)
        settings_layout.addLayout(path_layout)
        
        # 截图保存路径
        screenshot_path_layout = QHBoxLayout()
        screenshot_path_layout.addWidget(QLabel("截图路径:"))
        self.screenshot_path_input = QLineEdit()
        self.screenshot_path_input.setReadOnly(True)
        screenshot_path_layout.addWidget(self.screenshot_path_input)
        self.browse_screenshot_btn = QPushButton("浏览")
        self.browse_screenshot_btn.clicked.connect(self.browse_screenshot_path)
        screenshot_path_layout.addWidget(self.browse_screenshot_btn)
        settings_layout.addLayout(screenshot_path_layout)
        
        # 检测间隔
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("检测间隔(秒):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setMinimum(60)
        self.interval_spin.setMaximum(3600)
        self.interval_spin.setValue(60)
        self.interval_spin.setSuffix(" 秒")
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch()
        settings_layout.addLayout(interval_layout)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始监控")
        self.start_btn.clicked.connect(self.toggle_monitoring)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        btn_layout.addWidget(self.start_btn)
        
        self.save_config_btn = QPushButton("保存设置")
        self.save_config_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_config_btn)
        
        btn_layout.addStretch()
        settings_layout.addLayout(btn_layout)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 监控区域标记
        region_group = QGroupBox("监控区域")
        region_layout = QVBoxLayout()
        
        region_btn_layout = QHBoxLayout()
        self.add_region_btn = QPushButton("添加监控区域（截图标记）")
        self.add_region_btn.clicked.connect(self.add_monitor_region)
        region_btn_layout.addWidget(self.add_region_btn)
        
        self.clear_regions_btn = QPushButton("清空区域")
        self.clear_regions_btn.clicked.connect(self.clear_monitor_regions)
        region_btn_layout.addWidget(self.clear_regions_btn)
        region_btn_layout.addStretch()
        region_layout.addLayout(region_btn_layout)
        
        self.region_table = QTableWidget()
        self.region_table.setColumnCount(5)
        self.region_table.setHorizontalHeaderLabels(['名称', 'X坐标', 'Y坐标', '宽度', '高度'])
        self.region_table.horizontalHeader().setStretchLastSection(True)
        region_layout.addWidget(self.region_table)
        
        region_group.setLayout(region_layout)
        layout.addWidget(region_group)
        
        # 变化记录
        changes_group = QGroupBox("变化记录")
        changes_layout = QVBoxLayout()
        
        self.changes_text = QTextEdit()
        self.changes_text.setReadOnly(True)
        self.changes_text.setFont(QFont("Courier", 9))
        changes_layout.addWidget(self.changes_text)
        
        changes_group.setLayout(changes_layout)
        layout.addWidget(changes_group)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
    
    def load_config_to_ui(self):
        """加载配置到UI"""
        try:
            self.url_input.setText(self.config.get('target_url', ''))
            save_path = self.config.get('save_path', '')
            screenshot_path = self.config.get('screenshot_path', '')
            
            # 确保路径不为空，如果为空则使用默认值
            if not save_path:
                from pathlib import Path
                save_path = str(Path.home() / 'Desktop' / 'jianche1')
            
            if not screenshot_path:
                from pathlib import Path
                screenshot_path = str(Path.home() / 'Desktop' / 'jianche1' / 'screenshots')
            
            self.save_path_input.setText(save_path)
            self.screenshot_path_input.setText(screenshot_path)
            self.interval_spin.setValue(self.config.get('check_interval', 60))
            self.load_regions_to_table()
        except Exception as e:
            print(f"加载配置到UI时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def browse_save_path(self):
        """浏览保存路径"""
        try:
            current_path = self.save_path_input.text()
            if not current_path:
                from pathlib import Path
                current_path = str(Path.home() / 'Desktop')
            
            path = QFileDialog.getExistingDirectory(self, "选择保存路径", current_path)
            if path:
                self.save_path_input.setText(path)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"选择路径时出错: {str(e)}")
    
    def browse_screenshot_path(self):
        """浏览截图保存路径"""
        try:
            current_path = self.screenshot_path_input.text()
            if not current_path:
                from pathlib import Path
                current_path = str(Path.home() / 'Desktop')
            
            path = QFileDialog.getExistingDirectory(self, "选择截图保存路径", current_path)
            if path:
                self.screenshot_path_input.setText(path)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"选择路径时出错: {str(e)}")
    
    def add_monitor_region(self):
        """添加监控区域（通过截图标记）"""
        if not self.url_input.text():
            QMessageBox.warning(self, "提示", "请先输入监控网址")
            return
        
        # 打开截图标记窗口
        from ui.region_selector import RegionSelector
        selector = RegionSelector(self.url_input.text())
        if selector.exec_():
            region = selector.get_region()
            if region:
                regions = self.config.get('monitor_regions', [])
                regions.append(region)
                self.config['monitor_regions'] = regions
                self.load_regions_to_table()
    
    def load_regions_to_table(self):
        """加载区域到表格"""
        regions = self.config.get('monitor_regions', [])
        self.region_table.setRowCount(len(regions))
        for i, region in enumerate(regions):
            self.region_table.setItem(i, 0, QTableWidgetItem(region.get('name', f'区域{i+1}')))
            self.region_table.setItem(i, 1, QTableWidgetItem(str(region.get('x', 0))))
            self.region_table.setItem(i, 2, QTableWidgetItem(str(region.get('y', 0))))
            self.region_table.setItem(i, 3, QTableWidgetItem(str(region.get('width', 0))))
            self.region_table.setItem(i, 4, QTableWidgetItem(str(region.get('height', 0))))
    
    def clear_monitor_regions(self):
        """清空监控区域"""
        reply = QMessageBox.question(self, "确认", "确定要清空所有监控区域吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.config['monitor_regions'] = []
            self.load_regions_to_table()
    
    def save_settings(self):
        """保存设置"""
        try:
            # 验证路径
            save_path = self.save_path_input.text().strip()
            screenshot_path = self.screenshot_path_input.text().strip()
            
            if not save_path:
                QMessageBox.warning(self, "错误", "请设置保存路径")
                return
            
            if not screenshot_path:
                QMessageBox.warning(self, "错误", "请设置截图保存路径")
                return
            
            self.config['target_url'] = self.url_input.text().strip()
            self.config['save_path'] = save_path
            self.config['screenshot_path'] = screenshot_path
            self.config['check_interval'] = self.interval_spin.value()
            
            # 保存配置
            config.save_config(self.config)
            
            # 确保目录存在
            try:
                config.ensure_directories(self.config)
            except Exception as e:
                QMessageBox.warning(self, "警告", f"创建目录时出错: {str(e)}\n但设置已保存")
            
            QMessageBox.information(self, "成功", "设置已保存")
        
        except Exception as e:
            import traceback
            error_msg = f"保存设置时出错:\n{str(e)}\n\n详细信息:\n{traceback.format_exc()}"
            QMessageBox.critical(self, "错误", error_msg)
            print(error_msg)  # 同时在控制台输出
    
    def toggle_monitoring(self):
        """切换监控状态"""
        if not self.monitoring:
            if not self.url_input.text():
                QMessageBox.warning(self, "提示", "请先输入监控网址并保存设置")
                return
            
            self.save_settings()
            self.start_monitoring()
        else:
            self.stop_monitoring()
    
    def start_monitoring(self):
        """开始监控"""
        try:
            self.monitoring = True
            self.start_btn.setText("停止监控")
            self.start_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px;")
            self.statusBar().showMessage("正在初始化浏览器...")
            
            # 延迟初始化监控器，避免阻塞UI
            try:
                # 初始化监控器
                if not self.monitor:
                    self.statusBar().showMessage("正在初始化浏览器驱动，请稍候...")
                    self.monitor = WebMonitor(self.config['target_url'], 
                                             self.config.get('monitor_regions', []))
                    self.statusBar().showMessage("浏览器初始化成功，开始监控...")
                
                # 立即执行一次检查（在后台线程中执行）
                self.check_changes()
                
                # 启动定时器
                interval_ms = self.config['check_interval'] * 1000
                self.timer.start(interval_ms)
                self.statusBar().showMessage("监控已启动")
            
            except Exception as e:
                import traceback
                error_msg = f"初始化浏览器失败: {str(e)}"
                self.statusBar().showMessage("监控启动失败")
                
                # 恢复按钮状态
                self.monitoring = False
                self.start_btn.setText("开始监控")
                self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
                
                # 显示详细错误信息
                detail_msg = f"{error_msg}\n\n可能的原因：\n1. Chrome浏览器未安装\n2. Chrome驱动下载失败\n3. 网络连接问题\n\n详细信息:\n{traceback.format_exc()}"
                QMessageBox.critical(self, "启动监控失败", detail_msg)
                
                # 清理
                if self.monitor:
                    try:
                        self.monitor.close()
                    except:
                        pass
                    self.monitor = None
                
                print(detail_msg)
        
        except Exception as e:
            import traceback
            error_msg = f"启动监控时发生未知错误: {str(e)}\n\n{traceback.format_exc()}"
            QMessageBox.critical(self, "严重错误", error_msg)
            print(error_msg)
            
            # 恢复状态
            self.monitoring = False
            self.start_btn.setText("开始监控")
            self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        self.start_btn.setText("开始监控")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        self.statusBar().showMessage("已停止监控")
        
        self.timer.stop()
        if self.monitor:
            self.monitor.close()
            self.monitor = None
    
    def check_changes(self):
        """检查变化"""
        if not self.monitoring:
            return
        
        try:
            if not self.monitor:
                try:
                    self.statusBar().showMessage("正在初始化浏览器...")
                    self.monitor = WebMonitor(self.config['target_url'],
                                             self.config.get('monitor_regions', []))
                except Exception as e:
                    error_msg = f"初始化浏览器失败: {str(e)}"
                    self.statusBar().showMessage(error_msg)
                    self.changes_text.append(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {error_msg}\n")
                    # 停止监控
                    self.stop_monitoring()
                    QMessageBox.warning(self, "监控失败", f"{error_msg}\n\n监控已停止")
                    return
            
            # 获取当前数据
            try:
                self.statusBar().showMessage("正在检查变化...")
                new_data = self.monitor.extract_product_info()
            except Exception as e:
                error_msg = f"提取数据失败: {str(e)}"
                self.statusBar().showMessage(error_msg)
                self.changes_text.append(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {error_msg}\n")
                return
            
            old_data = self.config.get('last_data', {})
            
            # 比较变化
            changes = self.monitor.compare_data(old_data, new_data)
            
            if changes:
                # 有变化，记录并截图
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                try:
                    # 保存截图
                    screenshot_dir = self.config.get('screenshot_path', '')
                    os.makedirs(screenshot_dir, exist_ok=True)
                    
                    screenshot_filename = f"change_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    screenshot_path = os.path.join(screenshot_dir, screenshot_filename)
                    
                    # 获取全页截图
                    self.monitor.get_page_screenshot(screenshot_path)
                    
                    # 记录变化
                    change_log = {
                        'timestamp': timestamp,
                        'changes': changes,
                        'screenshot': screenshot_filename,
                        'all_data': new_data
                    }
                    
                    # 保存到文件
                    data_dir = self.config.get('data_path', '')
                    os.makedirs(data_dir, exist_ok=True)
                    log_file = os.path.join(data_dir, f"change_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                    with open(log_file, 'w', encoding='utf-8') as f:
                        json.dump(change_log, f, ensure_ascii=False, indent=2)
                    
                    # 显示在UI
                    log_text = f"\n[{timestamp}] 检测到变化:\n"
                    for change in changes:
                        log_text += f"  - {change['field']}: {change['old_value']} -> {change['new_value']}\n"
                    log_text += f"  截图已保存: {screenshot_filename}\n"
                    
                    self.changes_text.append(log_text)
                    self.statusBar().showMessage(f"检测到变化！时间: {timestamp}")
                    
                except Exception as e:
                    error_msg = f"保存截图或日志失败: {str(e)}"
                    self.statusBar().showMessage(error_msg)
                    self.changes_text.append(f"\n[{timestamp}] 检测到变化，但保存失败: {error_msg}\n")
                
                # 更新配置中的最后数据
                self.config['last_data'] = new_data
                try:
                    config.save_config(self.config)
                except:
                    pass
            
            else:
                # 无变化，只更新时间
                self.config['last_data'] = new_data
                try:
                    config.save_config(self.config)
                except:
                    pass
                self.statusBar().showMessage(f"监控中... 上次检查: {datetime.now().strftime('%H:%M:%S')} (无变化)")
        
        except Exception as e:
            import traceback
            error_msg = f"检查变化时出错: {str(e)}"
            self.statusBar().showMessage(error_msg)
            error_detail = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {error_msg}\n详细信息:\n{traceback.format_exc()}\n"
            self.changes_text.append(error_detail)
            print(error_detail)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.monitoring:
            self.stop_monitoring()
        event.accept()

