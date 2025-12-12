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
import os


class ConfigManager:
    """配置管理器 - iOS版本"""
    
    def __init__(self):
        # iOS应用数据目录
        try:
            if sys.platform == 'ios':
                # iOS上使用Documents目录
                home_dir = Path(os.environ.get('HOME', '/var/mobile'))
                self.config_dir = home_dir / 'Documents' / 'ECHWorkersClient'
            else:
                # 其他平台使用home目录
                self.config_dir = Path.home() / '.echworkers'
            
            self.config_file = self.config_dir / 'config.json'
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"[DEBUG] 配置目录: {self.config_dir}")
            print(f"[DEBUG] 配置文件: {self.config_file}")
            
        except Exception as e:
            print(f"[ERROR] 初始化配置目录失败: {e}")
            # 降级使用临时目录
            self.config_dir = Path('/tmp/echworkers')
            self.config_file = self.config_dir / 'config.json'
            try:
                self.config_dir.mkdir(parents=True, exist_ok=True)
            except:
                pass
        
        self.servers = []
        self.current_server_id = None
        
    def load_config(self):
        """加载配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.servers = data.get('servers', [])
                    self.current_server_id = data.get('current_server_id')
                    print(f"[DEBUG] 成功加载配置: {len(self.servers)} 个服务器")
        except Exception as e:
            print(f"[ERROR] 加载配置失败: {e}")
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
            print(f"[DEBUG] 配置已保存")
        except Exception as e:
            print(f"[ERROR] 保存配置失败: {e}")
    
    def add_default_server(self):
        """添加默认服务器"""
        try:
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
            print(f"[DEBUG] 已添加默认服务器")
        except Exception as e:
            print(f"[ERROR] 添加默认服务器失败: {e}")
    
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
        print("[DEBUG] ========== 应用启动 ==========")
        print(f"[DEBUG] Python版本: {sys.version}")
        print(f"[DEBUG] 平台: {sys.platform}")
        print(f"[DEBUG] 工作目录: {os.getcwd()}")
        
        try:
            self.config_manager = ConfigManager()
            self.config_manager.load_config()
            self.process = None
            self.is_running = False
            
            print("[DEBUG] 配置管理器初始化成功")
            
            # 创建主窗口
            self.main_window = toga.MainWindow(title=self.formal_name)
            
            print("[DEBUG] 开始创建UI")
            # 创建UI组件
            self.create_ui()
            
            print("[DEBUG] UI创建完成")
            # 显示主窗口
            self.main_window.content = self.main_box
            self.main_window.show()
            
            print("[DEBUG] ========== 应用启动完成 ==========")
            
        except Exception as e:
            print(f"[CRITICAL ERROR] 应用启动失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def create_ui(self):
        """创建用户界面"""
        try:
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
            
            # 添加启动日志
            self.append_log(f"[系统] ECH Workers 已启动\n")
            self.append_log(f"[系统] 平台: {sys.platform}\n")
            self.append_log(f"[系统] 版本: 1.2.0\n")
            self.append_log(f"[提示] 配置代理后，在系统设置中手动配置SOCKS5代理\n")
            self.append_log(f"[提示] 代理地址: 127.0.0.1:30000\n\n")
            
        except Exception as e:
            print(f"[ERROR] 创建UI失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def load_current_config(self):
        """加载当前配置到UI"""
        try:
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
        except Exception as e:
            print(f"[ERROR] 加载配置到UI失败: {e}")
    
    def save_config(self, widget):
        """保存配置"""
        try:
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
        except Exception as e:
            print(f"[ERROR] 保存配置失败: {e}")
            self.append_log(f"[错误] 保存配置失败: {e}\n")
    
    def start_proxy(self, widget):
        """启动代理"""
        try:
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
            threading.Thread(target=self._run_proxy, daemon=True).start()
            
            self.is_running = True
            self.start_button.enabled = False
            self.stop_button.enabled = True
        except Exception as e:
            print(f"[ERROR] 启动代理失败: {e}")
            self.append_log(f"[错误] 启动失败: {e}\n")
    
    def _run_proxy(self):
        """在后台线程运行代理"""
        try:
            # 查找ech-workers二进制文件
            # 在iOS打包后，应该在app bundle的resources中
            binary_name = 'ech-workers'
            
            # 尝试多个可能的位置
            possible_paths = [
                # iOS bundle中的资源
                Path(self.paths.app) / 'resources' / binary_name,
                Path(self.paths.app) / binary_name,
                # 开发环境
                Path(__file__).parent / 'resources' / binary_name,
                # 系统路径
                Path('/usr/local/bin') / binary_name,
            ]
            
            binary_path = None
            for path in possible_paths:
                if path.exists():
                    binary_path = str(path)
                    break
            
            if not binary_path:
                self.append_log(f"[错误] 未找到ech-workers二进制文件\n")
                self.append_log(f"[提示] 尝试的路径:\n")
                for p in possible_paths:
                    self.append_log(f"  - {p}\n")
                return
            
            self.append_log(f"[系统] 找到二进制: {binary_path}\n")
            
            # 构建命令
            cmd = [binary_path]
            
            server = self.config_manager.get_current_server()
            if server['server']:
                cmd.extend(['-f', server['server']])
            if server['listen']:
                cmd.extend(['-l', server['listen']])
            if server['token']:
                cmd.extend(['-token', server['token']])
            if server['ip']:
                cmd.extend(['-ip', server['ip']])
            if server['dns']:
                cmd.extend(['-dns', server['dns']])
            if server['ech']:
                cmd.extend(['-ech', server['ech']])
            
            self.append_log(f"[系统] 执行命令: {' '.join(cmd)}\n")
            
            # 启动进程
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1
            )
            
            self.append_log("[系统] 代理已启动\n")
            
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
            print(f"[ERROR] 运行代理失败: {e}")
            import traceback
            traceback.print_exc()
            self.append_log(f"[错误] 运行失败: {str(e)}\n")
        finally:
            self.is_running = False
            self.start_button.enabled = True
            self.stop_button.enabled = False
    
    def stop_proxy(self, widget):
        """停止代理"""
        try:
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
        except Exception as e:
            print(f"[ERROR] 停止代理失败: {e}")
    
    def append_log(self, text):
        """添加日志"""
        try:
            current = self.log_view.value or ''
            self.log_view.value = current + text
            
            # 限制日志长度
            if len(self.log_view.value) > 10000:
                self.log_view.value = self.log_view.value[-10000:]
        except Exception as e:
            print(f"[ERROR] 添加日志失败: {e}")
    
    def clear_log(self, widget):
        """清空日志"""
        try:
            self.log_view.value = ''
            self.append_log("[系统] 日志已清空\n")
        except Exception as e:
            print(f"[ERROR] 清空日志失败: {e}")


def main():
    """应用入口"""
    try:
        print("[DEBUG] 创建应用实例")
        return ECHWorkersApp(
            'ECH Workers',
            'com.echworkers.client'
        )
    except Exception as e:
        print(f"[CRITICAL ERROR] 应用创建失败: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == '__main__':
    try:
        app = main()
        app.main_loop()
    except Exception as e:
        print(f"[CRITICAL ERROR] 应用运行失败: {e}")
        import traceback
        traceback.print_exc()



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
            if server['dns']:
                cmd.extend(['-dns', server['dns']])
            if server['ech']:
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
