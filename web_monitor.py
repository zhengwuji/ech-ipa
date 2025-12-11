# 网页监控模块
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from bs4 import BeautifulSoup
import requests
from PIL import Image
import io
import os
import json
from browser_detector import detect_browsers, get_browser_name, get_browser_driver_name
from driver_validator import is_valid_exe, test_driver

class WebMonitor:
    def __init__(self, url, monitor_regions=None, browser_path=None):
        self.url = url
        self.monitor_regions = monitor_regions or []
        self.driver = None
        self.browser_path = browser_path
        self.browser_type = None
        self.setup_driver()
    
    def setup_driver(self):
        """初始化浏览器驱动 - 自动检测并使用系统默认浏览器"""
        import shutil
        
        try:
            # 检测所有已安装的浏览器
            browsers = detect_browsers()
            
            if not browsers:
                raise Exception(
                    "未找到已安装的浏览器！\n\n"
                    "请安装以下浏览器之一：\n"
                    "1. Google Chrome\n"
                    "2. Microsoft Edge\n"
                    "3. Mozilla Firefox（仅部分支持）"
                )
            
            # 优先使用默认浏览器，然后是Chrome，最后是Edge
            browser_path = None
            browser_type = None
            
            if self.browser_path and os.path.exists(self.browser_path):
                # 使用指定的浏览器路径
                browser_path = self.browser_path
                browser_type = get_browser_name(browser_path)
            elif 'default' in browsers:
                browser_path = browsers['default']
                browser_type = get_browser_name(browser_path)
            elif 'chrome' in browsers:
                browser_path = browsers['chrome']
                browser_type = 'chrome'
            elif 'edge' in browsers:
                browser_path = browsers['edge']
                browser_type = 'edge'
            else:
                # 使用第一个找到的浏览器
                browser_path = list(browsers.values())[0]
                browser_type = get_browser_name(browser_path)
            
            self.browser_type = browser_type
            print(f"使用浏览器: {browser_type} - {browser_path}")
            
            # 根据浏览器类型初始化
            if browser_type == 'edge' or (browser_type == 'unknown' and 'edge' in browser_path.lower()):
                self._setup_edge_driver(browser_path)
            else:
                # Chrome 或基于 Chromium 的浏览器
                self._setup_chrome_driver(browser_path)
        
        except Exception as e:
            error_msg = str(e)
            print(error_msg)
            raise Exception(error_msg) from e
    
    def _setup_chrome_driver(self, browser_path):
        """初始化Chrome驱动"""
        import shutil
        
        options = ChromeOptions()
        options.add_argument('--headless')  # 无头模式
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        if browser_path:
            options.binary_location = browser_path
        
        cache_path = os.path.join(os.path.expanduser("~"), ".wdm")
        max_retries = 3
        
        for retry in range(max_retries):
            try:
                if retry > 0:
                    # 清除缓存并重新下载
                    if os.path.exists(cache_path):
                        shutil.rmtree(cache_path, ignore_errors=True)
                    print(f"第 {retry + 1} 次尝试下载驱动...")
                
                driver_path = ChromeDriverManager().install()
                
                # 验证驱动文件存在
                if not os.path.exists(driver_path):
                    if retry < max_retries - 1:
                        continue
                    raise Exception(f"驱动文件不存在: {driver_path}")
                
                # 验证文件大小
                file_size = os.path.getsize(driver_path)
                if file_size < 100 * 1024:
                    print(f"警告: 驱动文件太小 ({file_size} 字节)，可能损坏")
                    if retry < max_retries - 1:
                        continue
                
                # 验证PE文件格式
                if not is_valid_exe(driver_path):
                    print(f"警告: 驱动文件格式无效，重新下载...")
                    if retry < max_retries - 1:
                        continue
                    raise Exception(f"驱动文件格式无效: {driver_path}")
                
                # 测试驱动是否可以运行
                if not test_driver(driver_path):
                    print(f"警告: 驱动文件无法运行，重新下载...")
                    if retry < max_retries - 1:
                        continue
                
                # 尝试初始化浏览器
                service = ChromeService(driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
                self.driver.set_page_load_timeout(30)
                print(f"✓ Chrome驱动初始化成功 (大小: {file_size} 字节)")
                return
                
            except Exception as e:
                error_msg = str(e)
                if "WinError 193" in error_msg or "不是有效的Win32" in error_msg:
                    if retry < max_retries - 1:
                        print(f"驱动验证失败，重试中... (尝试 {retry + 1}/{max_retries})")
                        continue
                # 如果是最后一次重试，抛出异常
                raise
        
        # 如果所有重试都失败
        raise Exception(
            "驱动下载和验证失败，已尝试多次\n\n"
            "请尝试以下解决方案：\n"
            f"1. 运行 '清理驱动缓存.bat' 或手动删除: {cache_path}\n"
            "2. 检查网络连接并重试\n"
            "3. 如果安装了防病毒软件，请临时禁用或添加例外\n"
            "4. 重新启动程序，程序会自动重新下载驱动"
        )
    
    def _setup_edge_driver(self, browser_path):
        """初始化Edge驱动"""
        import shutil
        
        options = EdgeOptions()
        options.add_argument('--headless')  # 无头模式
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        if browser_path:
            options.binary_location = browser_path
        
        try:
            cache_path = os.path.join(os.path.expanduser("~"), ".wdm")
            max_retries = 3
            
            for retry in range(max_retries):
                try:
                    if retry > 0:
                        if os.path.exists(cache_path):
                            shutil.rmtree(cache_path, ignore_errors=True)
                        print(f"第 {retry + 1} 次尝试下载Edge驱动...")
                    
                    driver_path = EdgeChromiumDriverManager().install()
                    
                    if not os.path.exists(driver_path):
                        if retry < max_retries - 1:
                            continue
                        raise Exception(f"驱动文件不存在: {driver_path}")
                    
                    file_size = os.path.getsize(driver_path)
                    if file_size < 100 * 1024:
                        if retry < max_retries - 1:
                            continue
                    
                    if not is_valid_exe(driver_path):
                        if retry < max_retries - 1:
                            continue
                        raise Exception(f"驱动文件格式无效: {driver_path}")
                    
                    if not test_driver(driver_path):
                        if retry < max_retries - 1:
                            continue
                    
                    service = EdgeService(driver_path)
                    self.driver = webdriver.Edge(service=service, options=options)
                    self.driver.set_page_load_timeout(30)
                    print(f"✓ Edge驱动初始化成功 (大小: {file_size} 字节)")
                    return
                    
                except Exception as e:
                    error_msg = str(e)
                    if "WinError 193" in error_msg or "不是有效的Win32" in error_msg:
                        if retry < max_retries - 1:
                            continue
                    raise
            
            raise Exception("驱动下载和验证失败，已尝试多次")
            
        except Exception as driver_error:
            error_msg = str(driver_error)
            
            if "WinError 193" in error_msg or "不是有效的Win32" in error_msg:
                try:
                    cache_path = os.path.join(os.path.expanduser("~"), ".wdm")
                    if os.path.exists(cache_path):
                        shutil.rmtree(cache_path, ignore_errors=True)
                    driver_path = EdgeChromiumDriverManager().install()
                    service = EdgeService(driver_path)
                    self.driver = webdriver.Edge(service=service, options=options)
                    self.driver.set_page_load_timeout(30)
                except Exception as retry_error:
                    raise Exception(
                        f"Edge浏览器驱动初始化失败 (WinError 193): {str(retry_error)}\n\n"
                        f"请尝试以下解决方案：\n"
                        f"1. 运行 '清理驱动缓存.bat' 清除缓存\n"
                        f"2. 手动删除驱动缓存文件夹: {cache_path}\n"
                        f"3. 检查网络连接并重试\n"
                        f"4. 重新安装Edge浏览器"
                    ) from retry_error
            else:
                raise Exception(
                    f"Edge浏览器驱动初始化失败: {error_msg}\n\n"
                    f"请确保：\n"
                    f"1. 已安装Edge浏览器\n"
                    f"2. 网络连接正常（需要下载驱动）\n"
                    f"3. 有足够的磁盘空间"
                ) from driver_error
    
    def get_page_screenshot(self, save_path=None):
        """获取整个页面截图"""
        if not self.driver:
            self.setup_driver()
        
        self.driver.get(self.url)
        time.sleep(3)  # 等待页面加载
        
        screenshot = self.driver.get_screenshot_as_png()
        img = Image.open(io.BytesIO(screenshot))
        
        if save_path:
            img.save(save_path)
        
        return img
    
    def get_region_screenshot(self, region, save_path=None):
        """获取指定区域的截图"""
        if not self.driver:
            self.setup_driver()
        
        self.driver.get(self.url)
        time.sleep(3)
        
        screenshot = self.driver.get_screenshot_as_png()
        full_img = Image.open(io.BytesIO(screenshot))
        
        # 裁剪区域
        x = region.get('x', 0)
        y = region.get('y', 0)
        width = region.get('width', 0)
        height = region.get('height', 0)
        
        region_img = full_img.crop((x, y, x + width, y + height))
        
        if save_path:
            region_img.save(save_path)
        
        return region_img
    
    def extract_product_info(self):
        """提取产品信息（价格、销售量、评价）"""
        if not self.driver:
            self.setup_driver()
        
        self.driver.get(self.url)
        time.sleep(3)
        
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        info = {
            'price': None,
            'sales': None,
            'rating': None,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 通用选择器，根据不同网站调整
        # 价格
        price_selectors = [
            '.price', '.product-price', '[class*="price"]',
            '.current-price', '.price-current', '#price'
        ]
        for selector in price_selectors:
            try:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    # 提取数字
                    import re
                    price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                    if price_match:
                        info['price'] = price_match.group()
                    break
            except:
                continue
        
        # 销售量
        sales_selectors = [
            '.sales', '.product-sales', '[class*="sales"]',
            '.sold-count', '.sales-count'
        ]
        for selector in sales_selectors:
            try:
                sales_elem = soup.select_one(selector)
                if sales_elem:
                    sales_text = sales_elem.get_text(strip=True)
                    import re
                    sales_match = re.search(r'\d+', sales_text)
                    if sales_match:
                        info['sales'] = sales_match.group()
                    break
            except:
                continue
        
        # 评价
        rating_selectors = [
            '.rating', '.product-rating', '[class*="rating"]',
            '.score', '.review-score'
        ]
        for selector in rating_selectors:
            try:
                rating_elem = soup.select_one(selector)
                if rating_elem:
                    rating_text = rating_elem.get_text(strip=True)
                    import re
                    rating_match = re.search(r'[\d.]+', rating_text)
                    if rating_match:
                        info['rating'] = rating_match.group()
                    break
            except:
                continue
        
        return info
    
    def compare_data(self, old_data, new_data):
        """比较数据变化"""
        changes = []
        
        for key in ['price', 'sales', 'rating']:
            old_value = old_data.get(key)
            new_value = new_data.get(key)
            
            if old_value is not None and new_value is not None:
                if str(old_value) != str(new_value):
                    changes.append({
                        'field': key,
                        'old_value': old_value,
                        'new_value': new_value,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        return changes
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None

