#!/usr/bin/env python3
# 更新walkthrough.md添加VPN权限增强功能说明

walkthrough_path = r'C:\Users\Administrator\.gemini\antigravity\brain\36fab38e-4208-4f26-9967-431c425132ea\walkthrough.md'

# 读取文件
with open(walkthrough_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在"---\n\n## 总结"前添加新内容
vpn_enhancement = """---

## VPN权限增强功能 (commits: d41e4ce, c26559c)

### 用户反馈
用户在TrollStore上成功安装应用，但显示SOCKS5模式而非VPN模式，说明VPN权限未获取。

### 实施的改进

#### 1. 增强TrollStore检测 (d41e4ce)
- 从3个路径增加到6个检测路径
- 添加系统路径访问权限检查
- 支持用户手动启用TrollStore模式
- 每个检测步骤都输出详细日志

#### 2. 手动请求UI (c26559c)
在SOCKS5模式下显示蓝色提示框，包含：
- **重新检测TrollStore** 按钮
- **手动请求VPN权限** 按钮

### 用户使用流程

**场景1：自动检测成功**
- 应用启动自动检测TrollStore
- 显示"VPN模式"
- 点击"启动VPN（一键）"

**场景2：检测失败需要手动**
- 应用显示"SOCKS5模式"
- 查看诊断日志了解原因
- 点击"手动请求VPN权限"
- 系统弹出权限请求，允许后重启应用

### 技术亮点
- ✅ 6个TrollStore检测路径
- ✅ 系统路径权限检查
- ✅ 用户手动启用选项
- ✅ 详细的诊断日志
- ✅ 友好的UI提示和按钮

"""

# 插入新内容
content = content.replace('---\r\n\r\n## 总结', vpn_enhancement + '\r\n---\r\n\r\n## 总结')

# 写回文件
with open(walkthrough_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ walkthrough.md 已更新")
print("添加了VPN权限增强功能说明")
