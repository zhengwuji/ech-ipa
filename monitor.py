import json
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

from PIL import Image
import pytesseract
from playwright.sync_api import sync_playwright

import config
import version


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


class MonitorWorker:
    def __init__(self, conf: Dict[str, Any], on_log, on_change, on_status):
        self.conf = conf
        self.on_log = on_log
        self.on_change = on_change
        self.on_status = on_status
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.last_text = conf.get("last_text", "")
        self.last_fullshot = ""

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)

    def _run_loop(self):
        self.on_status("监控已启动")
        while not self.stop_event.is_set():
            try:
                interval = max(60, int(self.conf.get("check_interval", 60)))
                result = self._check_once()
                if result:
                    old_text, new_text, shot_path = result
                    self.last_text = new_text
                    self.conf["last_text"] = new_text
                    config.save_config(self.conf)
                    log = {
                        "time": datetime.now().isoformat(),
                        "field": "监控区域文本",
                        "old": old_text,
                        "new": new_text,
                        "screenshot": shot_path,
                        "version": version.current_version(),
                    }
                    data_dir = self.conf.get("data_path", ".")
                    os.makedirs(data_dir, exist_ok=True)
                    json_path = os.path.join(data_dir, f"change_log_{timestamp()}.json")
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(log, f, ensure_ascii=False, indent=2)
                    self.on_change(log)
                time.sleep(interval)
            except Exception as exc:  # pragma: no cover - runtime safety
                self.on_log(f"监控出错: {exc}")
                time.sleep(60)
        self.on_status("监控已停止")

    def _check_once(self):
        url = self.conf.get("target_url", "").strip()
        region = self.conf.get("region")
        if not url:
            self.on_log("未设置监控网址")
            return None
        if not region:
            self.on_log("未选择监控区域")
            return None

        image, shot_path = self._capture_page(url)
        if image is None:
            return None
        self.last_fullshot = shot_path
        text = self._extract_region_text(image, region)
        if text is None:
            return None
        normalized = text.strip()
        if normalized != self.last_text:
            old = self.last_text
            self.on_log(f"检测到变化: {old} -> {normalized}")
            return old, normalized, shot_path
        self.on_log("本轮无变化")
        return None

    def _capture_page(self, url: str):
        screenshot_dir = self.conf.get("screenshot_path", ".")
        os.makedirs(screenshot_dir, exist_ok=True)
        shot_file = os.path.join(screenshot_dir, f"page_{timestamp()}.png")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(3000)
            page.screenshot(path=shot_file, full_page=True)
            browser.close()

        try:
            image = Image.open(shot_file)
            return image, shot_file
        except Exception as exc:  # pragma: no cover
            self.on_log(f"加载截图失败: {exc}")
            return None, shot_file

    def _extract_region_text(self, image: Image.Image, region: Dict[str, Any]) -> Optional[str]:
        try:
            x = int(image.width * region["x_ratio"])
            y = int(image.height * region["y_ratio"])
            w = int(image.width * region["w_ratio"])
            h = int(image.height * region["h_ratio"])
            cropped = image.crop((x, y, x + w, y + h))
            text = pytesseract.image_to_string(cropped, lang="eng+chi_sim")
            return text
        except Exception as exc:  # pragma: no cover
            self.on_log(f"OCR 失败: {exc}")
            return None

