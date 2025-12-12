import Foundation

class ProxyConfigGenerator {
    static let shared = ProxyConfigGenerator()
    
    private init() {}
    
    func generateShadowrocketConfig(server: String, port: String, token: String, alias: String = "ECH-Worker") -> String {
        // Shadowrocket format:
        // SOCKS5: socks5://user:pass@host:port?remarks=Alias
        // Since we are running a local SOCKS5 proxy, we point to 127.0.0.1
        // But usually users want to export the server config itself.
        // However, for ECH, the client runs locally. So the "config" for Shadowrocket
        // should probably point to the local SOCKS5 proxy started by this app.
        
        let localPort = "30000" // Default local port
        let config = "socks5://127.0.0.1:\(localPort)?remarks=\(alias)"
        
        // Base64 encode for sharing
        if let data = config.data(using: .utf8) {
            return "ss://" + data.base64EncodedString()
        }
        return config
    }
    
    func generateClashConfig(localPort: String = "30000") -> String {
        return """
        proxies:
          - name: "ECH-Worker"
            type: socks5
            server: 127.0.0.1
            port: \(localPort)
            # username: 
            # password: 
            # tls: false
            # skip-cert-verify: true
            # udp: true
        """
    }
    
    func generateSurgeConfig(localPort: String = "30000") -> String {
        return """
        [Proxy]
        ECH-Worker = socks5, 127.0.0.1, \(localPort)
        """
    }
    
    func generateMobileConfig(localPort: String) -> String {
        let uuid = UUID().uuidString
        let identifier = "com.echworkers.proxy.\(UUID().uuidString)"
        
        return """
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>PayloadContent</key>
            <array>
                <dict>
                    <key>PayloadDescription</key>
                    <string>Configures local SOCKS5 proxy for ECH Workers</string>
                    <key>PayloadDisplayName</key>
                    <string>ECH Workers Local Proxy</string>
                    <key>PayloadIdentifier</key>
                    <string>\(identifier)</string>
                    <key>PayloadType</key>
                    <string>com.apple.proxy.http.global</string>
                    <key>PayloadUUID</key>
                    <string>\(uuid)</string>
                    <key>PayloadVersion</key>
                    <integer>1</integer>
                    <key>ProxyType</key>
                    <string>Manual</string>
                    <key>ProxyServer</key>
                    <string>127.0.0.1</string>
                    <key>ProxyServerPort</key>
                    <integer>\(localPort)</integer>
                    <key>ProxyUsername</key>
                    <string></string>
                    <key>ProxyPassword</key>
                    <string></string>
                    <key>ProxyCaptiveLoginAllowed</key>
                    <false/>
                </dict>
            </array>
            <key>PayloadDisplayName</key>
            <string>ECH Workers Proxy Config</string>
            <key>PayloadIdentifier</key>
            <string>\(identifier).profile</string>
            <key>PayloadRemovalDisallowed</key>
            <false/>
            <key>PayloadType</key>
            <string>Configuration</string>
            <key>PayloadUUID</key>
            <string>\(UUID().uuidString)</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
        </dict>
        </plist>
        """
    }

    // Helper to generate a shareable URL or file content
    func generateShareableConfig(type: String, localPort: String) -> String {
        switch type.lowercased() {
        case "shadowrocket":
            return "socks5://127.0.0.1:\(localPort)?remarks=ECH-Worker"
        case "clash":
            return generateClashConfig(localPort: localPort)
        case "surge":
            return generateSurgeConfig(localPort: localPort)
        case "mobileconfig":
            return generateMobileConfig(localPort: localPort)
        default:
            return "socks5://127.0.0.1:\(localPort)"
        }
    }
}
