#!/usr/bin/env python3
# 修复 ContentView.swift - 移除 ProxyConfigGenerator 引用

import re

content_view_path = r'C:\Users\Administrator\Desktop\ech-ipa\swift-ios\ContentView.swift'

# 读取原始文件
with open(content_view_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到shareProxyConfig函数并替换
output_lines = []
in_share_proxy_function = False
skip_until_closing_brace = False
brace_count = 0

for i, line in enumerate(lines):
    # 检测函数开始
    if 'func shareProxyConfig()' in line:
        in_share_proxy_function = True
        skip_until_closing_brace = True
        brace_count = 0
        # 添加新的简化实现
        output_lines.append(line)
        output_lines.append('        // TODO: 配置文件生成功能暂时禁用\r\n')
        output_lines.append('        // ProxyConfigGenerator.swift 需要单独添加到 Xcode 项目中\r\n')
        output_lines.append('        appendLog("[提示] 配置文件生成功能暂时不可用")\r\n')
        output_lines.append('        appendLog("[提示] 请手动配置 SOCKS5 代理: 127.0.0.1:\\(listenPort)")\r\n')
        continue
    
    if skip_until_closing_brace:
        # 统计大括号
        brace_count += line.count('{')
        brace_count -= line.count('}')
        
        # 如果找到闭合的大括号
        if brace_count < 0:
            output_lines.append('    }\r\n')
            skip_until_closing_brace = False
            in_share_proxy_function = False
            brace_count = 0
            continue
    else:
        output_lines.append(line)

# 写回文件
with open(content_view_path, 'w', encoding='utf-8') as f:
    f.writelines(output_lines)

print("✅ ContentView.swift 已更新")
print("shareProxyConfig() 函数已简化，移除了ProxyConfigGenerator引用")
