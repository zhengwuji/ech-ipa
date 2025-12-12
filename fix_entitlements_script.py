#!/usr/bin/env python3
# 修复 create_xcode_project.sh 中的 entitlements 配置

import re

script_path = r'C:\Users\Administrator\Desktop\ech-ipa\swift-ios\create_xcode_project.sh'

with open(script_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 确保在 Build Settings 中添加 CODE_SIGN_ENTITLEMENTS
# 查找 Release 配置
if 'CODE_SIGN_ENTITLEMENTS = ECHWorkers.entitlements;' not in content:
    content = content.replace(
        'ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME = AccentColor;\n				CODE_SIGN_IDENTITY = "";',
        'ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME = AccentColor;\n				CODE_SIGN_ENTITLEMENTS = ECHWorkers.entitlements;\n				CODE_SIGN_IDENTITY = "";'
    )

# 2. 确保文件复制命令正确
if '# Info.plist 和 ECHWorkers.entitlements 保持在根目录' not in content:
    content = content.replace(
        '# Info.plist保持在根目录',
        '# Info.plist 和 ECHWorkers.entitlements 保持在根目录'
    )

with open(script_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ create_xcode_project.sh entitlements 配置已修复")
