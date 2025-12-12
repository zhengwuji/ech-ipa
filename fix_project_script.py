#!/usr/bin/env python3
# 修复 create_xcode_project.sh - 添加 ProxyConfigGenerator.swift

import re

script_path = r'C:\Users\Administrator\Desktop\ech-ipa\swift-ios\create_xcode_project.sh'

# 读取原始文件
with open(script_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在PBXBuildFile section添加
content = content.replace(
    '\tA1000003000000000000001 /* ECHNetworkManager.swift in Sources */ = {isa = PBXBuildFile; fileRef = A2000003000000000000001 /* ECHNetworkManager.swift */; };\r\n',
    '\tA1000003000000000000001 /* ECHNetworkManager.swift in Sources */ = {isa = PBXBuildFile; fileRef = A2000003000000000000001 /* ECHNetworkManager.swift */; };\r\n\tA1000004000000000000001 /* ProxyConfigGenerator.swift in Sources */ = {isa = PBXBuildFile; fileRef = A2000005000000000000001 /* ProxyConfigGenerator.swift */; };\r\n'
)

# 2. 在PBXFileReference section添加  
content = content.replace(
    '\tA2000004000000000000001 /* Info.plist */ = {isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = Info.plist; sourceTree = "<group>"; };\r\n',
    '\tA2000004000000000000001 /* Info.plist */ = {isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = Info.plist; sourceTree = "<group>"; };\r\n\tA2000005000000000000001 /* ProxyConfigGenerator.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = ProxyConfigGenerator.swift; sourceTree = "<group>"; };\r\n'
)

# 3. 在PBXGroup children添加
content = content.replace(
    '\t\t\t\tA2000003000000000000001 /* ECHNetworkManager.swift */,\r\n\t\t\t\tA2000004000000000000001 /* Info.plist */,\r\n',
    '\t\t\t\tA2000003000000000000001 /* ECHNetworkManager.swift */,\r\n\t\t\t\tA2000005000000000000001 /* ProxyConfigGenerator.swift */,\r\n\t\t\t\tA2000004000000000000001 /* Info.plist */,\r\n'
)

# 4. 在Sources files添加
content = content.replace(
    '\t\t\t\tA1000003000000000000001 /* ECHNetworkManager.swift in Sources */,\r\n\t\t\t);\r\n',
    '\t\t\t\tA1000003000000000000001 /* ECHNetworkManager.swift in Sources */,\r\n\t\t\t\tA1000004000000000000001 /* ProxyConfigGenerator.swift in Sources */,\r\n\t\t\t);\r\n'
)

# 5. 添加文件复制
content = content.replace(
    'cp ECHNetworkManager.swift ECHWorkers/ 2>/dev/null || true\r\n',
    'cp ECHNetworkManager.swift ECHWorkers/  2>/dev/null || true\r\ncp ProxyConfigGenerator.swift ECHWorkers/ 2>/dev/null || true\r\n'
)

# 6. 更新项目包含列表
content = content.replace(
    'echo "  - ECHNetworkManager.swift (纯 Swift 网络层)"\r\n',
    'echo "  - ECHNetworkManager.swift (纯 Swift 网络层)"\r\necho "  - ProxyConfigGenerator.swift (配置文件生成器)"\r\n'
)

# 写回文件
with open(script_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ ProxyConfigGenerator.swift 已成功添加到项目配置中")
print("修改的部分:")
print("  - PBXBuildFile section")
print("  - PBXFileReference section")
print("  - PBXGroup children")
print("  - Sources files")
print("  - 文件复制命令")
print("  - 项目包含列表")
