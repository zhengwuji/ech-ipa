import plistlib
import sys

# Read mobileprovision file (it's a signed plist wrapped in CMS)
with open(r'C:\Users\Administrator\Desktop\ech-ipa\1111\Etisalat - Emirates Telecommunications Corporation.mobileprovision', 'rb') as f:
    data = f.read()

# Find the plist data (between <?xml and </plist>)
start = data.find(b'<?xml')
end = data.find(b'</plist>') + len(b'</plist>')

if start != -1 and end != -1:
    plist_data = data[start:end]
    
    # Parse the plist
    plist = plistlib.loads(plist_data)
    
    print("=" * 60)
    print("Provisioning Profile 信息分析")
    print("=" * 60)
    
    # Check for entitlements
    if 'Entitlements' in plist:
        entitlements = plist['Entitlements']
        
        print("\n【权限列表 (Entitlements)】:")
        for key, value in entitlements.items():
            print(f"  - {key}: {value}")
        
        print("\n" + "=" * 60)
        print("【VPN/Network Extension 权限检查】:")
        print("=" * 60)
        
        # Check for Network Extension capabilities
        vpn_keys = [
            'com.apple.developer.networking.networkextension',
            'com.apple.developer.networking.vpn.api',
            'com.apple.developer.networking.HotspotConfiguration',
            'com.apple.developer.networking.wifi-info'
        ]
        
        has_vpn = False
        for key in vpn_keys:
            if key in entitlements:
                print(f"✅ 找到: {key}")
                print(f"   值: {entitlements[key]}")
                has_vpn = True
        
        if not has_vpn:
            print("❌ 没有找到任何VPN/Network Extension相关权限")
            print("\n需要的权限:")
            print("  - com.apple.developer.networking.networkextension")
            print("\n结论: 当前证书 **不支持VPN功能**")
        else:
            print("\n✅ 结论: 当前证书 **支持VPN功能**")
    
    # Show App ID
    if 'AppIDName' in plist:
        print(f"\n【App ID名称】: {plist['AppIDName']}")
    
    # Show expiration
    if 'ExpirationDate' in plist:
        print(f"【过期时间】: {plist['ExpirationDate']}")
        
else:
    print("错误: 无法解析mobileprovision文件")
