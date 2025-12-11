# 网页监控模块
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
from PIL import Image
import io
import os
import json

class WebMonitor:
    def __init__(self, url, monitor_regions=None):
        self.url = url
        self.monitor_regions = monitor_regions or []
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """初始化浏览器驱动"""
        import platform
        import subprocess
        import shutil
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 无头模式
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            # 首先检查Chrome是否安装
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
            ]
            
            chrome_path = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break
            
            if chrome_path:
                chrome_options.binary_location = chrome_path
            
            # 尝试安装Chrome驱动
            try:
                # 清除可能损坏的驱动缓存
                cache_path = os.path.join(os.path.expanduser("~"), ".wdm")
                
                driver_path = ChromeDriverManager().install()
                
                # 验证驱动文件是否有效
                if not os.path.exists(driver_path):
                    raise Exception(f"驱动文件不存在: {driver_path}")
                
                # 检查文件大小（有效的驱动应该大于100KB）
                file_size = os.path.getsize(driver_path)
                if file_size < 100 * 1024:  # 小于100KB可能有问题
                    print(f"警告: 驱动文件可能损坏，大小: {file_size} 字节")
                    # 删除可能损坏的文件，重新下载
                    try:
                        os.remove(driver_path)
                        driver_path = ChromeDriverManager().install()
                    except:
                        pass
                
                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.driver.set_page_load_timeout(30)  # 设置页面加载超时
                
            except Exception as driver_error:
                # 如果自动下载失败，尝试其他方法
                error_msg = str(driver_error)
                
                # 检查是否是WinError 193
                if "WinError 193" in error_msg or "不是有效的Win32" in error_msg:
                    # 清除缓存并重试
                    try:
                        cache_path = os.path.join(os.path.expanduser("~"), ".wdm")
                        if os.path.exists(cache_path):
                            import shutil
                            shutil.rmtree(cache_path, ignore_errors=True)
                        # 重新下载
                        driver_path = ChromeDriverManager().install()
                        service = Service(driver_path)
                        self.driver = webdriver.Chrome(service=service, options=chrome_options)
                        self.driver.set_page_load_timeout(30)
                    except Exception as retry_error:
                        raise Exception(
                            f"浏览器驱动初始化失败 (WinError 193): {str(retry_error)}\n\n"
                            f"请尝试以下解决方案：\n"
                            f"1. 确保Chrome浏览器已正确安装\n"
                            f"2. 手动删除驱动缓存文件夹: {cache_path}\n"
                            f"3. 检查网络连接并重试\n"
                            f"4. 如果问题持续，请重新安装Chrome浏览器"
                        ) from retry_error
                else:
                    raise Exception(
                        f"浏览器驱动初始化失败: {error_msg}\n\n"
                        f"请确保：\n"
                        f"1. 已安装Chrome浏览器\n"
                        f"2. 网络连接正常（需要下载驱动）\n"
                        f"3. 有足够的磁盘空间"
                    ) from driver_error
        
        except Exception as e:
            error_msg = str(e)
            print(error_msg)
            raise Exception(error_msg) from e
    
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

