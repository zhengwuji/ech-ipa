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
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 无头模式
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            print(f"浏览器驱动初始化失败: {e}")
            raise
    
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

