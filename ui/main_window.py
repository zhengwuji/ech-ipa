import os
import shutil
import threading
from datetime import datetime

from PyQt5 import QtCore, QtWidgets
import keyboard

import config
import monitor
from ui.region_selector import RegionSelector
import version


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("网站监控工具 - Windows10 样式")
        self.conf = config.load_config()
        self.worker = None
        self.hotkey_handle = None
        self._build_ui()
        self._load_conf_to_form()
        self._bind_hotkey()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout()

        form = QtWidgets.QFormLayout()
        self.url_edit = QtWidgets.QLineEdit()
        form.addRow("监控网址：", self.url_edit)

        self.interval_spin = QtWidgets.QSpinBox()
        self.interval_spin.setMinimum(60)
        self.interval_spin.setMaximum(3600)
        form.addRow("检测间隔(秒)：", self.interval_spin)

        self.save_path_edit = QtWidgets.QLineEdit()
        self.save_path_btn = QtWidgets.QPushButton("浏览")
        self.save_path_btn.clicked.connect(self._choose_save_path)
        sp_row = QtWidgets.QHBoxLayout()
        sp_row.addWidget(self.save_path_edit)
        sp_row.addWidget(self.save_path_btn)
        form.addRow("数据保存路径：", sp_row)

        self.screenshot_path_edit = QtWidgets.QLineEdit()
        self.screenshot_path_btn = QtWidgets.QPushButton("浏览")
        self.screenshot_path_btn.clicked.connect(self._choose_screenshot_path)
        sc_row = QtWidgets.QHBoxLayout()
        sc_row.addWidget(self.screenshot_path_edit)
        sc_row.addWidget(self.screenshot_path_btn)
        form.addRow("截图保存路径：", sc_row)

        self.hotkey_edit = QtWidgets.QLineEdit()
        self.hotkey_edit.setPlaceholderText("例如：F9 或 ctrl+shift+s")
        form.addRow("截图快捷键：", self.hotkey_edit)

        layout.addLayout(form)

        btn_row = QtWidgets.QHBoxLayout()
        self.capture_btn = QtWidgets.QPushButton("获取页面截图并选择区域")
        self.capture_btn.clicked.connect(self._capture_reference)
        self.start_btn = QtWidgets.QPushButton("开始监控")
        self.start_btn.clicked.connect(self._toggle_monitor)
        btn_row.addWidget(self.capture_btn)
        btn_row.addWidget(self.start_btn)
        layout.addLayout(btn_row)

        self.status_label = QtWidgets.QLabel("就绪")
        layout.addWidget(self.status_label)

        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        self.setLayout(layout)
        self.resize(900, 600)

    def _load_conf_to_form(self):
        self.url_edit.setText(self.conf.get("target_url", ""))
        self.interval_spin.setValue(int(self.conf.get("check_interval", 60)))
        self.save_path_edit.setText(self.conf.get("save_path", ""))
        self.screenshot_path_edit.setText(self.conf.get("screenshot_path", ""))
        self.hotkey_edit.setText(self.conf.get("hotkey", "F9"))

    def _read_form_to_conf(self):
        self.conf["target_url"] = self.url_edit.text().strip()
        self.conf["check_interval"] = max(60, self.interval_spin.value())
        self.conf["save_path"] = self.save_path_edit.text().strip()
        self.conf["screenshot_path"] = self.screenshot_path_edit.text().strip()
        self.conf["data_path"] = self.conf["save_path"]
        self.conf["hotkey"] = self.hotkey_edit.text().strip() or "F9"
        config.save_config(self.conf)

    def _choose_save_path(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择数据保存路径", self.save_path_edit.text())
        if path:
            self.save_path_edit.setText(path)
            self._read_form_to_conf()

    def _choose_screenshot_path(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择截图保存路径", self.screenshot_path_edit.text())
        if path:
            self.screenshot_path_edit.setText(path)
            self._read_form_to_conf()

    def _capture_reference(self):
        self._read_form_to_conf()
        url = self.conf.get("target_url", "").strip()
        if not url:
            self._log("请先填写监控网址")
            return

        def task():
            self._set_status("正在获取页面截图...")
            shot_path = self._quick_capture(url)
            if not shot_path:
                self._set_status("截图失败")
                return
            self._set_status("请选择要监控的区域")

            def open_selector():
                selector = RegionSelector(shot_path, self._on_region_selected)
                selector.show()
                selector.raise_()
                selector.activateWindow()

            QtCore.QTimer.singleShot(0, open_selector)

        threading.Thread(target=task, daemon=True).start()

    def _quick_capture(self, url):
        screenshot_dir = self.conf.get("screenshot_path", ".")
        os.makedirs(screenshot_dir, exist_ok=True)
        shot_file = os.path.join(screenshot_dir, f"ref_{monitor.timestamp()}.png")
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1400, "height": 900})
                page.goto(url, wait_until="networkidle")
                page.wait_for_timeout(3000)
                page.screenshot(path=shot_file, full_page=True)
                browser.close()
            return shot_file
        except Exception as exc:
            self._log(f"截图失败: {exc}")
            return None

    def _on_region_selected(self, region):
        if not region:
            self._log("未保存区域")
            return
        self.conf["region"] = region
        config.save_config(self.conf)
        self._log("监控区域已保存")

    def _toggle_monitor(self):
        if self.worker and self.worker.thread and self.worker.thread.is_alive():
            self.worker.stop()
            self.start_btn.setText("开始监控")
            return
        self._read_form_to_conf()
        self.worker = monitor.MonitorWorker(self.conf, self._log, self._on_change, self._set_status)
        self.worker.start()
        self.start_btn.setText("停止监控")

    def _on_change(self, log):
        msg = f"时间: {log['time']}\n字段: {log['field']}\n原值: {log['old']}\n新值: {log['new']}\n截图: {log['screenshot']}\n版本: {log['version']}\n"
        self._log(msg)

    def _set_status(self, text):
        def set_label():
            self.status_label.setText(text)
        QtCore.QMetaObject.invokeMethod(self.status_label, "setText", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, text))
        self._log(text)

    def _log(self, text):
        def append():
            self.log_view.append(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")
        QtCore.QMetaObject.invokeMethod(self.log_view, "append", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, f"[{datetime.now().strftime('%H:%M:%S')}] {text}"))

    def _bind_hotkey(self):
        key = self.conf.get("hotkey", "F9")
        if self.hotkey_handle:
            keyboard.remove_hotkey(self.hotkey_handle)
        self.hotkey_handle = keyboard.add_hotkey(key, self._manual_snapshot)

    def _manual_snapshot(self):
        if not self.worker or not self.worker.last_fullshot:
            self._log("暂无可保存的截图")
            return
        target_dir = self.conf.get("screenshot_path", ".")
        os.makedirs(target_dir, exist_ok=True)
        new_path = os.path.join(target_dir, f"manual_{monitor.timestamp()}.png")
        shutil.copy(self.worker.last_fullshot, new_path)
        self._log(f"手动截图已保存：{new_path}")

