"""
ECH Workers Proxy Client - iOS Edition
使用 Toga 框架构建的 iOS 原生应用
"""

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import json
import subprocess
import threading
from pathlib import Path
import sys


class ConfigManager:
    """配置管理器 - iOS版本"""
    
    def __init__(self):
        # iOS应用数据目录
        if sys.platform == 'ios':
            import os
            self.config_dir = Path(os.getenv('HOME')) / 'Documents' / 'ECHWorkersClient'
        else:
            self.config_dir = Path.home() / '.echworkers'
        
        self.config_file = self.config_dir / 'config.json'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.servers = []
        self.current_server_id = None
        
    def load_config(self):
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.servers = data.get('servers', [])
                    self.current_server_id = data.get('current_server_id')
            except Exception as e:
                print(f"加载配置失败: {e}")
                self.servers = []
                self.current_server_id = None
        
        if not self.servers:
            self.add_default_server()
    
    def save_config(self):
        """保存配置"""
        try:
            data = {
                'servers': self.servers,
                'current_server_id': self.current_server_id
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def add_default_server(self):
        """添加默认服务器"""
        import uuid
        default_server = {
            'id': str(uuid.uuid4()),
            'name': '默认服务器',
            'server': 'example.com:443',
            'listen': '127.0.0.1:30000',
            'token': '',
            'ip': 'saas.sin.fan',
            'dns': 'dns.alidns.com/dns-query',
            'ech': 'cloudflare-ech.com',
            'routing_mode': 'bypass_cn'
        }
        self.servers.append(default_server)
        self.current_server_id = default_server['id']
        self.save_config()
    
    def get_current_server(self):
        """获取当前服务器配置"""
        if self.current_server_id:
            for server in self.servers:
                if server['id'] == self.current_server_id:
                    return server
        return self.servers[0] if self.servers else None


class ECHWorkersApp(toga.App):
    """ECH Workers iOS 主应用"""
    
    def startup(self):
        """应用启动"""
        self.config_manager = ConfigManager()
        self.config_manager.load_config()
        self.process = None
        self.is_running = False
        
        # 创建主窗口
        self.main_window = toga.MainWindow(title=self.formal_name)
        
        # 创建UI组件
        self.create_ui()
        
        # 显示主窗口
        self.main_window.content = self.main_box
        self.main_window.show()
    
    def create_ui(self):
        """创建用户界面"""
        
        # 服务器配置区域
        server_label = toga.Label('服务地址:', style=Pack(padding=5))
        self.server_input = toga.TextInput(
            placeholder='example.com:443',
            style=Pack(flex=1, padding=5)
        )
        
        listen_label = toga.Label('监听地址:', style=Pack(padding=5))
        self.listen_input = toga.TextInput(
            placeholder='127.0.0.1:30000',
            style=Pack(flex=1, padding=5)
        )
        
        token_label = toga.Label('身份令牌:', style=Pack(padding=5))
        self.token_input = toga.TextInput(
            placeholder='可选',
            style=Pack(flex=1, padding=5)
        )
        
        # 高级选项
        ip_label = toga.Label('优选IP:', style=Pack(padding=5))
        self.ip_input = toga.TextInput(
            placeholder='saas.sin.fan',
            style=Pack(flex=1, padding=5)
        )
        
        dns_label = toga.Label('DOH服务器:', style=Pack(padding=5))
        self.dns_input = toga.TextInput(
            placeholder='dns.alidns.com/dns-query',
            style=Pack(flex=1, padding=5)
        )
        
        ech_label = toga.Label('ECH域名:', style=Pack(padding=5))
        self.ech_input = toga.TextInput(
            placeholder='cloudflare-ech.com',
            style=Pack(flex=1, padding=5)
        )
        
        # 分流模式选择
        routing_label = toga.Label('代理模式:', style=Pack(padding=5))
        self.routing_select = toga.Selection(
            items=['全局代理', '跳过中国大陆', '不改变代理'],
            style=Pack(flex=1, padding=5)
        )
        
        # 控制按钮
        self.start_button = toga.Button(
            '启动代理',
            on_press=self.start_proxy,
            style=Pack(padding=5, flex=1)
        )
        
        self.stop_button = toga.Button(
            '停止代理',
            on_press=self.stop_proxy,
            enabled=False,
            style=Pack(padding=5, flex=1)
        )
        
        self.save_button = toga.Button(
            '保存配置',
            on_press=self.save_config,
            style=Pack(padding=5, flex=1)
        )
        
        # 日志显示区域
        log_label = toga.Label('运行日志:', style=Pack(padding=5))
        self.log_view = toga.MultilineTextInput(
            readonly=True,
            style=Pack(flex=1, padding=5, height=200)
        )
        
        self.clear_log_button = toga.Button(
            '清空日志',
            on_press=self.clear_log,
            style=Pack(padding=5)
        )
        
        # 加载当前配置
        self.load_current_config()
        
        # 布局
        server_box = toga.Box(
            children=[server_label, self.server_input],
            style=Pack(direction=ROW, padding=5)
        )
        
        listen_box = toga.Box(
            children=[listen_label, self.listen_input],
            style=Pack(direction=ROW, padding=5)
        )
        
        token_box = toga.Box(
            children=[token_label, self.token_input],
            style=Pack(direction=ROW, padding=5)
        )
        
        ip_box = toga.Box(
            children=[ip_label, self.ip_input],
            style=Pack(direction=ROW, padding=5)
        )
        
        dns_box = toga.Box(
            children=[dns_label, self.dns_input],
            style=Pack(direction=ROW, padding=5)
        )
        
        ech_box = toga.Box(
            children=[ech_label, self.ech_input],
            style=Pack(direction=ROW, padding=5)
        )
        
        routing_box = toga.Box(
            children=[routing_label, self.routing_select],
            style=Pack(direction=ROW, padding=5)
        )
        
        button_box = toga.Box(
            children=[self.start_button, self.stop_button, self.save_button],
            style=Pack(direction=ROW, padding=5)
        )
        
        log_header_box = toga.Box(
            children=[log_label, self.clear_log_button],
            style=Pack(direction=ROW, padding=5)
        )
        
        # 主容器
        self.main_box = toga.Box(
            children=[
                server_box,
                listen_box,
                token_box,
                ip_box,
                dns_box,
                ech_box,
                routing_box,
                button_box,
                log_header_box,
                self.log_view,
            ],
            style=Pack(direction=COLUMN, padding=10)
        )
    
    def load_current_config(self):
        """加载当前配置到UI"""
        server = self.config_manager.get_current_server()
        if server:
            self.server_input.value = server.get('server', '')
            self.listen_input.value = server.get('listen', '')
            self.token_input.value = server.get('token', '')
            self.ip_input.value = server.get('ip', '')
            self.dns_input.value = server.get('dns', '')
            self.ech_input.value = server.get('ech', '')
            
            # 设置分流模式
            routing_mode = server.get('routing_mode', 'bypass_cn')
            if routing_mode == 'global':
                self.routing_select.value = '全局代理'
            elif routing_mode == 'bypass_cn':
                self.routing_select.value = '跳过中国大陆'
            else:
                self.routing_select.value = '不改变代理'
    
    def save_config(self, widget):
        """保存配置"""
        server = self.config_manager.get_current_server()
        if server:
            server['server'] = self.server_input.value
            server['listen'] = self.listen_input.value
            server['token'] = self.token_input.value
            server['ip'] = self.ip_input.value
            server['dns'] = self.dns_input.value
            server['ech'] = self.ech_input.value
            
            # 保存分流模式
            routing = self.routing_select.value
            if routing == '全局代理':
                server['routing_mode'] = 'global'
            elif routing == '跳过中国大陆':
                server['routing_mode'] = 'bypass_cn'
            else:
                server['routing_mode'] = 'none'
            
            self.config_manager.save_config()
            self.append_log("[系统] 配置已保存\n")
            self.main_window.info_dialog('成功', '配置已保存')
    
    def start_proxy(self, widget):
        """启动代理"""
        if self.is_running:
            self.main_window.info_dialog('提示', '代理已在运行中')
            return
        
        # 检查必填项
        if not self.server_input.value:
            self.main_window.error_dialog('错误', '请填写服务地址')
            return
        
        if not self.listen_input.value:
            self.main_window.error_dialog('错误', '请填写监听地址')
            return
        
        # 保存当前配置
        self.save_config(None)
        
        # 启动代理
        self.append_log("[系统] 正在启动代理...\n")
        
        # 在iOS上，需要使用编译好的二进制文件
        # 这里假设ech-workers二进制文件已经打包到应用中
        threading.Thread(target=self._run_proxy, daemon=True).start()
        
        self.is_running = True
        self.start_button.enabled = False
        self.stop_button.enabled = True
    
    def _run_proxy(self):
        """在后台线程运行代理"""
        try:
            # 构建命令
            # 注意：在iOS上，需要使用打包进应用的可执行文件
            # 这里简化处理，实际需要找到bundled资源
            cmd = ['ech-workers']
            
            server = self.config_manager.get_current_server()
            if server['server']:
                cmd.extend(['-f', server['server']])
            if server['listen']:
                cmd.extend(['-l', server['listen']])
            if server['token']:
                cmd.extend(['-token', server['token']])
            if server['ip']:
                cmd.extend(['-ip', server['ip']])
            if server['dns'] and server['dns'] != 'dns.alidns.com/dns-query':
                cmd.extend(['-dns', server['dns']])
            if server['ech'] and server['ech'] != 'cloudflare-ech.com':
                cmd.extend(['-ech', server['ech']])
            
            self.append_log(f"[系统] 执行命令: {' '.join(cmd)}\n")
            
            # 启动进程
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1
            )
            
            # 读取输出
            for line in iter(self.process.stdout.readline, b''):
                if not self.is_running:
                    break
                try:
                    decoded_line = line.decode('utf-8', errors='replace')
                    self.append_log(decoded_line)
                except:
                    pass
            
            self.process.wait()
            self.append_log("[系统] 代理已停止\n")
            
        except Exception as e:
            self.append_log(f"[错误] 启动失败: {str(e)}\n")
        finally:
            self.is_running = False
            self.start_button.enabled = True
            self.stop_button.enabled = False
    
    def stop_proxy(self, widget):
        """停止代理"""
        if not self.is_running:
            return
        
        self.append_log("[系统] 正在停止代理...\n")
        self.is_running = False
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except:
                try:
                    self.process.kill()
                except:
                    pass
        
        self.start_button.enabled = True
        self.stop_button.enabled = False
    
    def append_log(self, text):
        """添加日志"""
        current = self.log_view.value or ''
        self.log_view.value = current + text
        
        # 限制日志长度
        if len(self.log_view.value) > 10000:
            self.log_view.value = self.log_view.value[-10000:]
    
    def clear_log(self, widget):
        """清空日志"""
        self.log_view.value = ''
        self.append_log("[系统] 日志已清空\n")


def main():
    """应用入口"""
    return ECHWorkersApp(
        'ECH Workers',
        'com.echworkers.client'
    )


if __name__ == '__main__':
    main().main_loop()
