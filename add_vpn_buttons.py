#!/usr/bin/env python3
# 添加VPN手动请求按钮到ContentView.swift

content_view_path = r'C:\Users\Administrator\Desktop\ech-ipa\swift-ios\ContentView.swift'

# 读取文件
with open(content_view_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找"Divider()"行，在它之前插入VPN诊断部分
output_lines = []
inserted = False

for i, line in enumerate(lines):
    # 找到第179行附近的Divider
    if 'Divider()' in line and '.padding(.vertical, 5)' in lines[i+1] if i+1 < len(lines) else False:
        if not inserted:
            # 插入VPN诊断UI
            output_lines.append('                    \r\n')
            output_lines.append('                    // VPN权限诊断和手动请求按钮（SOCKS5模式下显示）\r\n')
            output_lines.append('                    if !networkManager.isVPNAvailable {\r\n')
            output_lines.append('                        VStack(spacing: 10) {\r\n')
            output_lines.append('                            Text("TrollStore用户可尝试获取VPN权限")\r\n')
            output_lines.append('                                .font(.caption)\r\n')
            output_lines.append('                                .foregroundColor(.secondary)\r\n')
            output_lines.append('                            \r\n')
            output_lines.append('                            HStack(spacing: 10) {\r\n')
            output_lines.append('                                Button(action: {\r\n')
            output_lines.append('                                    networkManager.enableTrollStoreMode()\r\n')
            output_lines.append('                                }) {\r\n')
            output_lines.append('                                    HStack {\r\n')
            output_lines.append('                                        Image(systemName: "arrow.triangle.2.circlepath")\r\n')
            output_lines.append('                                        Text("重新检测TrollStore")\r\n')
            output_lines.append('                                    }\r\n')
            output_lines.append('                                    .font(.caption)\r\n')
            output_lines.append('                                    .padding(.vertical, 8)\r\n')
            output_lines.append('                                    .padding(.horizontal, 12)\r\n')
            output_lines.append('                                    .background(Color.purple)\r\n')
            output_lines.append('                                    .foregroundColor(.white)\r\n')
            output_lines.append('                                    .cornerRadius(8)\r\n')
            output_lines.append('                                }\r\n')
            output_lines.append('                                \r\n')
            output_lines.append('                                Button(action: {\r\n')
            output_lines.append('                                    networkManager.requestVPNPermission()\r\n')
            output_lines.append('                                }) {\r\n')
            output_lines.append('                                    HStack {\r\n')
            output_lines.append('                                        Image(systemName: "shield.lefthalf.filled")\r\n')
            output_lines.append('                                        Text("手动请求VPN权限")\r\n')
            output_lines.append('                                    }\r\n')
            output_lines.append('                                    .font(.caption)\r\n')
            output_lines.append('                                    .padding(.vertical, 8)\r\n')
            output_lines.append('                                    .padding(.horizontal, 12)\r\n')
            output_lines.append('                                    .background(Color.blue)\r\n')
            output_lines.append('                                    .foregroundColor(.white)\r\n')
            output_lines.append('                                    .cornerRadius(8)\r\n')
            output_lines.append('                                }\r\n')
            output_lines.append('                            }\r\n')
            output_lines.append('                        }\r\n')
            output_lines.append('                        .padding()\r\n')
            output_lines.append('                        .background(Color.blue.opacity(0.1))\r\n')
            output_lines.append('                        .cornerRadius(10)\r\n')
            output_lines.append('                        .padding(.horizontal)\r\n')
            output_lines.append('                    }\r\n')
            output_lines.append('                    \r\n')
            inserted = True
    
    output_lines.append(line)

# 写回文件
with open(content_view_path, 'w', encoding='utf-8') as f:
    f.writelines(output_lines)

print("✅ ContentView.swift 已更新")
print("添加了VPN诊断和手动请求按钮")
