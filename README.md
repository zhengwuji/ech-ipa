# ECH Workers Proxy - 跨平台版本

基于 ECH (Encrypted Client Hello) 技术的代理客户端，支持 **OpenWrt路由器**、**Windows/macOS桌面** 和 **iOS移动设备**。

## 📱 iOS版本

> **全新支持！** 现已支持iOS设备，可通过GitHub Releases下载IPA文件。

### iOS安装方法

**下载地址**: [GitHub Releases](https://github.com/zhengwuji/ech-ipa/releases) - 下载最新的 `ECHWorkers-unsigned.ipa`

#### 方法1: AltStore（推荐）
1. 在iOS设备上安装 [AltStore](https://altstore.io/)
2. 下载 `ECHWorkers-unsigned.ipa` 到设备
3. 在AltStore中打开IPA文件完成安装

#### 方法2: Sideloadly
1. 在电脑上安装 [Sideloadly](https://sideloadly.io/)
2. 下载 `ECHWorkers-unsigned.ipa`
3. 使用Sideloadly签名并通过USB安装到iOS设备

#### 方法3: 开发者证书
如果您有Apple开发者账户：
1. 使用 iOS App Signer 签名IPA
2. 通过Xcode或其他工具安装

### iOS使用说明
- 应用启动后，在"服务地址"填写您的Workers地址
- 配置监听地址（默认127.0.0.1:30000）
- 点击"启动代理"即可使用
- 支持全局代理和跳过中国大陆模式

---

## 🖥️ OpenWrt版本（路由器）

## ECH Workers Proxy for OpenWrt

基于 ECH (Encrypted Client Hello) 技术的代理客户端，专为 OpenWrt 路由器设计，带有 LuCI 管理界面。


Telegram 交流群：https://t.me/+ft-zI76oovgwNmRh

## 功能特性

- ✅ **一键安装** - 单个 IPK 包包含主程序和 LuCI 界面
- ✅ **LuCI 管理界面** - 图形化配置，无需命令行
- ✅ **多服务器管理** - 支持添加多个服务器配置，快速切换
- ✅ **分流设置** - 全局代理 / 跳过中国大陆 / 仅代理被墙站点
- ✅ **实时日志** - 查看运行状态，一键清空
- ✅ **开机自启** - 支持系统启动时自动运行
- ✅ **ECH 加密** - 加密 TLS 握手中的 SNI，保护隐私

## 快速安装教程

### 第一步：下载 IPK 包

从 [GitHub Releases](https://github.com/zhengwuji/ech-op/releases) 下载最新版本：

- **x86_64 架构**：`ech-wk_1.0.0-r1_x86_64.ipk`

> 💡 只需下载这一个文件，已包含主程序和 LuCI 界面！

### 第二步：安装 IPK 包

**方法一：通过 LuCI 界面安装（推荐）**

1. 登录 OpenWrt 管理界面
2. 进入 **系统 → 软件包**
3. 点击 **上传软件包**，选择下载的 IPK 文件
4. 点击 **安装**

**方法二：通过 SSH 命令安装**

```bash
# 上传 IPK 到路由器
scp ech-wk_1.0.0-r1_x86_64.ipk root@192.168.1.1:/tmp/

# SSH 登录路由器
ssh root@192.168.1.1

# 安装
opkg install /tmp/ech-wk_1.0.0-r1_x86_64.ipk
```

### 第三步：清除 LuCI 缓存

```bash
rm -rf /tmp/luci-*
```

然后刷新浏览器页面。

### 第四步：配置服务

1. 进入 **服务 → ECH Workers Proxy**
2. 在「服务器管理」中添加服务器：
   - **服务器名称**：自定义名称
   - **服务地址**：`your-worker.workers.dev:443`
   - **身份令牌**：您的 Token（可选）
   - 勾选 **当前使用**
3. 在「核心配置」中设置监听地址（默认 `127.0.0.1:30000`）
4. 在「分流设置」中选择代理模式
5. 在「服务控制」中启用服务
6. 点击 **保存并应用**

## LuCI 界面功能说明

| 功能模块 | 说明 |
|---------|------|
| **服务控制** | 运行状态显示、启用开关、开机自启 |
| **服务器管理** | 新增/删除服务器，选择当前使用的服务器 |
| **核心配置** | 设置监听地址 |
| **高级选项** | 优选IP/域名、DOH服务器、ECH域名 |
| **分流设置** | 全局代理 / 跳过中国大陆 / 仅代理被墙站点 / 直连 |
| **运行日志** | 实时查看日志，一键清空 |

## 命令行使用

如果您不使用 LuCI 界面，也可以直接通过命令行运行：

```bash
ech-wk -server your-worker.workers.dev:443 -listen 127.0.0.1:30000
```

**参数说明：**

| 参数 | 说明 | 默认值 |
|-----|------|--------|
| `-server` | 服务端地址（必需） | - |
| `-listen` | 监听地址 | `127.0.0.1:30000` |
| `-token` | 身份验证令牌 | - |
| `-ip` | 指定服务端 IP（绕过 DNS） | - |
| `-doh` | DoH 服务器 | `dns.alidns.com/dns-query` |
| `-ech` | ECH 查询域名 | `cloudflare-ech.com` |

**完整示例：**

```bash
ech-wk \
  -server your-worker.workers.dev:443 \
  -listen 0.0.0.0:30000 \
  -token your-token \
  -ip saas.sin.fan \
  -doh dns.alidns.com/dns-query \
  -ech cloudflare-ech.com
```

## 配置代理客户端

安装完成后，配置您的设备使用 SOCKS5 代理：

- **代理地址**：`路由器IP` 或 `127.0.0.1`
- **端口**：`30000`（或您自定义的端口）
- **代理类型**：SOCKS5

### 配合 PassWall 使用

1. 进入 PassWall → 节点列表
2. 添加 SOCKS5 节点：
   - 地址：`127.0.0.1`
   - 端口：`30000`
3. 在主配置中选择该节点

### 配合 OpenClash 使用

在配置文件中添加：

```yaml
proxies:
  - name: "ECH-Workers"
    type: socks5
    server: 127.0.0.1
    port: 30000
```

## 服务管理命令

```bash
# 启动服务
/etc/init.d/ech-wk start

# 停止服务
/etc/init.d/ech-wk stop

# 重启服务
/etc/init.d/ech-wk restart

# 查看状态
/etc/init.d/ech-wk status

# 启用开机自启
/etc/init.d/ech-wk enable

# 禁用开机自启
/etc/init.d/ech-wk disable

# 查看日志
cat /tmp/ech-wk.log
logread | grep ech-wk
```

## 常见问题

### Q: 安装后在服务菜单找不到？

执行以下命令后刷新页面：
```bash
rm -rf /tmp/luci-*
```

### Q: 如何完全卸载？

```bash
opkg remove ech-wk
rm -rf /tmp/luci-*
```

### Q: 性能优化建议？

- 使用「高级选项」中的「优选IP/域名」减少 DNS 查询
- 如果监听地址设为 `0.0.0.0`，记得配置防火墙规则

### Q: 升级到新版本？

```bash
# 卸载旧版本
opkg remove ech-wk

# 安装新版本
opkg install /tmp/ech-wk_x.x.x-r1_x86_64.ipk

# 清除缓存
rm -rf /tmp/luci-*
```

## 致谢

- 原始项目来源：[CF_NAT](https://t.me/CF_NAT)
- 中国IP列表：[mayaxcn/china-ip-list](https://github.com/mayaxcn/china-ip-list)

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
