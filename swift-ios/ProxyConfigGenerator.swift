import Foundation

/// 代理配置文件生成器 - 支持SOCKS5全局代理
class ProxyConfigGenerator {
    static func generateMobileConfig(proxyHost: String = "127.0.0.1", proxyPort: Int = 30000) -\u003e Data? {
        let uuid = UUID().uuidString
        
        let config = """
        \u003c?xml version="1.0" encoding="UTF-8"?\u003e
        \u003c!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"\u003e
        \u003cplist version="1.0"\u003e
        \u003cdict\u003e
            \u003ckey\u003ePayloadContent\u003c/key\u003e
            \u003carray\u003e
                \u003cdict\u003e
                    \u003ckey\u003ePayloadType\u003c/key\u003e
                    \u003cstring\u003ecom.apple.proxy.http.global\u003c/string\u003e
                    \u003ckey\u003ePayloadIdentifier\u003c/key\u003e
                    \u003cstring\u003ecom.echworkers.proxy.global\u003c/string\u003e
                    \u003ckey\u003ePayloadUUID\u003c/key\u003e
                    \u003cstring\u003e\(UUID().uuidString)\u003c/string\u003e
                    \u003ckey\u003ePayloadDisplayName\u003c/key\u003e
                    \u003cstring\u003e全局代理配置\u003c/string\u003e
                    \u003ckey\u003ePayloadVersion\u003c/key\u003e
                    \u003cinteger\u003e1\u003c/integer\u003e
                    \u003ckey\u003ePayloadDescription\u003c/key\u003e
                    \u003cstring\u003e配置系统使用 ECH Workers SOCKS5 代理\u003c/string\u003e
                    \u003ckey\u003eProxyType\u003c/key\u003e
                    \u003cstring\u003eManual\u003c/string\u003e
                    \u003ckey\u003eHTTPEnable\u003c/key\u003e
                    \u003cinteger\u003e1\u003c/integer\u003e
                    \u003ckey\u003eHTTPProxy\u003c/key\u003e
                    \u003cstring\u003e\(proxyHost)\u003c/string\u003e
                    \u003ckey\u003eHTTPPort\u003c/key\u003e
                    \u003cinteger\u003e\(proxyPort)\u003c/integer\u003e
                    \u003ckey\u003eHTTPProxyType\u003c/key\u003e
                    \u003cstring\u003eSOCKS\u003c/string\u003e
                    \u003ckey\u003eHTTPSEnable\u003c/key\u003e
                    \u003cinteger\u003e1\u003c/integer\u003e
                    \u003ckey\u003eHTTPSProxy\u003c/key\u003e
                    \u003cstring\u003e\(proxyHost)\u003c/string\u003e
                    \u003ckey\u003eHTTPSPort\u003c/key\u003e
                    \u003cinteger\u003e\(proxyPort)\u003c/integer\u003e
                    \u003ckey\u003eHTTPSProxyType\u003c/key\u003e
                    \u003cstring\u003eSOCKS\u003c/string\u003e
                    \u003ckey\u003eSOCKSEnable\u003c/key\u003e
                    \u003cinteger\u003e1\u003c/integer\u003e
                    \u003ckey\u003eSOCKSProxy\u003c/key\u003e
                    \u003cstring\u003e\(proxyHost)\u003c/string\u003e
                    \u003ckey\u003eSOCKSPort\u003c/key\u003e
                    \u003cinteger\u003e\(proxyPort)\u003c/integer\u003e
                \u003c/dict\u003e
            \u003c/array\u003e
            \u003ckey\u003ePayloadDisplayName\u003c/key\u003e
            \u003cstring\u003eECH Workers 代理配置\u003c/string\u003e
            \u003ckey\u003ePayloadIdentifier\u003c/key\u003e
            \u003cstring\u003ecom.echworkers.proxy\u003c/string\u003e
            \u003ckey\u003ePayloadRemovalDisallowed\u003c/key\u003e
            \u003cfalse/\u003e
            \u003ckey\u003ePayloadType\u003c/key\u003e
            \u003cstring\u003eConfiguration\u003c/string\u003e
            \u003ckey\u003ePayloadUUID\u003c/key\u003e
            \u003cstring\u003e\(uuid)\u003c/string\u003e
            \u003ckey\u003ePayloadVersion\u003c/key\u003e
            \u003cinteger\u003e1\u003c/integer\u003e
            \u003ckey\u003ePayloadDescription\u003c/key\u003e
            \u003cstring\u003e自动配置系统代理到 ECH Workers SOCKS5 服务器 (\(proxyHost):\(proxyPort))。使用完毕后可在"设置 → 通用 → VPN与设备管理"中删除此配置。\u003c/string\u003e
            \u003ckey\u003ePayloadOrganization\u003c/key\u003e
            \u003cstring\u003eECH Workers\u003c/string\u003e
        \u003c/dict\u003e
        \u003c/plist\u003e
        """
        
        return config.data(using: .utf8)
    }
    
    static func saveConfigToTemporaryFile() -\u003e URL? {
        guard let configData = generateMobileConfig() else {
            return nil
        }
        
        let tempDir = FileManager.default.temporaryDirectory
        let fileURL = tempDir.appendingPathComponent("ECHWorkers_Proxy.mobileconfig")
        
        do {
            try configData.write(to: fileURL)
            return fileURL
        } catch {
            print("保存配置文件失败: \(error)")
            return nil
        }
    }
}
