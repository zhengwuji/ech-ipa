import SwiftUI

@available(iOS 14.0, *)
struct ContentView: View {
    @StateObject private var networkManager = ECHNetworkManager()
    
    // 配置状态
    @State private var serverAddress = "example.com:443"
    @State private var listenPort: String = "30000"
    @State private var token = ""
    @State private var echDomain = "cloudflare-ech.com"
    @State private var dohServer = "dns.alidns.com/dns-query"
    
    // 前置代理配置
    @State private var useUpstreamProxy = false
    @State private var upstreamProxyHost = "192.168.1.100"
    @State private var upstreamProxyPort = "1082"
    
    // UI状态
    @State private var logText = ""
    @State private var showAdvanced = false
    @State private var showProxyConfig = false
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 20) {
                    // 状态卡片
                    VStack(spacing: 8) {
                        HStack {
                            Circle()
                                .fill(networkManager.isRunning ? Color.green : Color.red)
                                .frame(width: 12, height: 12)
                            Text(networkManager.isRunning ? "代理运行中" : "代理已停止")
                                .font(.headline)
                            Spacer()
                        }
                        if networkManager.isRunning {
                            Text("SOCKS5: 127.0.0.1:\(listenPort)")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                        
                        // 模式显示
                        HStack {
                            Image(systemName: networkManager.currentMode == .vpn ? "shield.fill" : "network")
                                .foregroundColor(networkManager.currentMode == .vpn ? .green : .blue)
                            Text("运行模式")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            Text(networkManager.currentMode.rawValue)
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundColor(networkManager.currentMode == .vpn ? .green : .blue)
                            Spacer()
                        }
                        
                        // 使用提示
                        if networkManager.currentMode == .socks5 && networkManager.isRunning {
                            Text("💡 提示：在 Shadowrocket 中添加 SOCKS5 服务器 127.0.0.1:\(listenPort)")
                                .font(.caption2)
                                .foregroundColor(.orange)
                                .padding(.top, 4)
                        }
                    }
                    .padding()
                    .background(networkManager.isRunning ? Color.green.opacity(0.1) : Color.red.opacity(0.1))
                    .cornerRadius(12)
                    
                    // 基础配置
                    VStack(alignment: .leading, spacing: 12) {
                        Text("基础配置")
                            .font(.headline)
                            .foregroundColor(.primary)
                        
                        VStack(spacing: 10) {
                            ConfigField(label: "服务器地址", text: $serverAddress, placeholder: "your-worker.workers.dev:443")
                            ConfigField(label: "监听端口", text: $listenPort, placeholder: "30000")
                            ConfigField(label: "身份令牌", text: $token, placeholder: "可选")
                        }
                    }
                    .padding()
                    .background(Color(UIColor.systemBackground))
                    .cornerRadius(12)
                    .shadow(radius: 2)
                    
                    // 高级选项
                    DisclosureGroup("高级选项（ECH配置）", isExpanded: $showAdvanced) {
                        VStack(spacing: 10) {
                            ConfigField(label: "ECH域名", text: $echDomain, placeholder: "cloudflare-ech.com")
                            ConfigField(label: "DOH服务器", text: $dohServer, placeholder: "dns.alidns.com/dns-query")
                            
                            Text("ECH 功能使用 iOS 原生支持，无需额外配置")
                                .font(.caption2)
                                .foregroundColor(.secondary)
                                .padding(.top, 5)
                        }
                        .padding(.top, 10)
                    }
                    .padding()
                    .background(Color(UIColor.systemBackground))
                    .cornerRadius(12)
                    .shadow(radius: 2)
                    
                    // 前置代理配置
                    DisclosureGroup("前置代理（上游代理）", isExpanded: $showProxyConfig) {
                        VStack(spacing: 10) {
                            Toggle("启用前置代理", isOn: $useUpstreamProxy)
                                .padding(.vertical, 5)
                            
                            if useUpstreamProxy {
                                ConfigField(label: "代理服务器", text: $upstreamProxyHost, placeholder: "192.168.1.100")
                                ConfigField(label: "代理端口", text: $upstreamProxyPort, placeholder: "1082")
                                
                                Text("💡 提示：用于解决地区封锁问题")
                                    .font(.caption2)
                                    .foregroundColor(.blue)
                                    .padding(.top, 5)
                                Text("先通过 Shadowrocket 等代理突破，再连接服务器")
                                    .font(.caption2)
                                    .foregroundColor(.secondary)
                            }
                        }
                        .padding(.top, 10)
                    }
                    .padding()
                    .background(Color(UIColor.systemBackground))
                    .cornerRadius(12)
                    .shadow(radius: 2)
                    
                    // 控制按钮
                    HStack(spacing: 15) {
                        Button(action: startProxy) {
                            HStack {
                                Image(systemName: "play.fill")
                                Text("启动代理")
                            }
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(networkManager.isRunning ? Color.gray : Color.green)
                            .foregroundColor(.white)
                            .cornerRadius(10)
                        }
                        .disabled(networkManager.isRunning)
                        
                        Button(action: stopProxy) {
                            HStack {
                                Image(systemName: "stop.fill")
                                Text("停止代理")
                            }
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(networkManager.isRunning ? Color.red : Color.gray)
                            .foregroundColor(.white)
                            .cornerRadius(10)
                        }
                        .disabled(!networkManager.isRunning)
                    }
                    .padding(.horizontal)
                    
                    Button("保存配置") {
                        saveConfig()
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(10)
                    .padding(.horizontal)
                    
                    // 日志显示
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("运行日志")
                                .font(.headline)
                            Spacer()
                            Button("清空") {
                                logText = ""
                                appendLog("[系统] 日志已清空")
                            }
                            .font(.caption)
                            .foregroundColor(.blue)
                        }
                        
                        ScrollView {
                            Text(logText)
                                .font(.system(.caption, design: .monospaced))
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(8)
                        }
                        .frame(height: 200)
                        .background(Color(UIColor.systemGray6))
                        .cornerRadius(8)
                    }
                    .padding()
                    .background(Color(UIColor.systemBackground))
                    .cornerRadius(12)
                    .shadow(radius: 2)
                    
                    // 使用提示
                    VStack(alignment: .leading, spacing: 4) {
                        Text("📱 使用提示")
                            .font(.caption)
                            .fontWeight(.bold)
                        Text("启动代理后，在系统设置中配置SOCKS5代理")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                        Text("设置 → Wi-Fi → HTTP代理 → 手动")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                        Text("服务器: 127.0.0.1 端口: \(listenPort)")
                            .font(.caption2)
                            .foregroundColor(.blue)
                            .fontWeight(.medium)
                        Text("✅ 使用 iOS 原生 ECH 加密")
                            .font(.caption2)
                            .foregroundColor(.green)
                            .fontWeight(.medium)
                            .padding(.top, 2)
                    }
                    .padding()
                    .background(Color.blue.opacity(0.1))
                    .cornerRadius(8)
                    .padding(.horizontal)
                }
                .padding()
            }
            .navigationTitle("ECH Workers")
            .navigationBarTitleDisplayMode(.inline)
        }
        .onAppear {
            loadConfig()
            setupNetworkManager()
            appendLog("[系统] ECH Workers 已启动")
            appendLog("[系统] 版本: 2.0.0 (纯 Swift + 原生 ECH)")
            appendLog("[提示] 填写服务器地址后点击启动代理")
        }
    }
    
    func setupNetworkManager() {
        networkManager.onLog = { [self] message in
            appendLog(message)
        }
    }
    
    func loadConfig() {
        let defaults = UserDefaults.standard
        serverAddress = defaults.string(forKey: "serverAddress") ?? "example.com:443"
        listenPort = defaults.string(forKey: "listenPort") ?? "30000"
        token = defaults.string(forKey: "token") ?? ""
        echDomain = defaults.string(forKey: "echDomain") ?? "cloudflare-ech.com"
        dohServer = defaults.string(forKey: "dohServer") ?? "dns.alidns.com/dns-query"
        
        // 加载前置代理配置
        useUpstreamProxy = defaults.bool(forKey: "useUpstreamProxy")
        upstreamProxyHost = defaults.string(forKey: "upstreamProxyHost") ?? "192.168.1.100"
        upstreamProxyPort = defaults.string(forKey: "upstreamProxyPort") ?? "1082"
        
        // 检测 VPN 权限
        networkManager.checkVPNAvailability()
    }
    
    func saveConfig() {
        let defaults = UserDefaults.standard
        defaults.set(serverAddress, forKey: "serverAddress")
        defaults.set(listenPort, forKey: "listenPort")
        defaults.set(token, forKey: "token")
        defaults.set(echDomain, forKey: "echDomain")
        defaults.set(dohServer, forKey: "dohServer")
        
        // 保存前置代理配置
        defaults.set(useUpstreamProxy, forKey: "useUpstreamProxy")
        defaults.set(upstreamProxyHost, forKey: "upstreamProxyHost")
        defaults.set(upstreamProxyPort, forKey: "upstreamProxyPort")
        
        appendLog("[系统] 配置已保存")
    }
    
    func startProxy() {
        guard !serverAddress.isEmpty else {
            appendLog("[错误] 请填写服务器地址")
            return
        }
        
        guard let port = UInt16(listenPort) else {
            appendLog("[错误] 无效的端口号")
            return
        }
        
        saveConfig()
        
        // 配置网络管理器
        networkManager.serverAddress = serverAddress
        networkManager.listenPort = port
        networkManager.token = token
        networkManager.echDomain = echDomain
        networkManager.dohServer = dohServer
        
        // 配置前置代理
        networkManager.useUpstreamProxy = useUpstreamProxy
        if useUpstreamProxy, let proxyPort = UInt16(upstreamProxyPort) {
            networkManager.upstreamProxyHost = upstreamProxyHost
            networkManager.upstreamProxyPort = proxyPort
            appendLog("[系统] 将通过前置代理 \(upstreamProxyHost):\(upstreamProxyPort) 连接")
        }
        
        do {
            try networkManager.start()
            appendLog("[系统] 正在获取 ECH 配置...")
        } catch {
            appendLog("[错误] 启动失败: \(error.localizedDescription)")
        }
    }
    
    func stopProxy() {
        networkManager.stop()
    }
    
    func appendLog(_ message: String) {
        let timestamp = DateFormatter.localizedString(from: Date(), dateStyle: .none, timeStyle: .medium)
        logText += "[\(timestamp)] \(message)\n"
    }
}

@available(iOS 14.0, *)
struct ConfigField: View {
    let label: String
    @Binding var text: String
    let placeholder: String
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
            TextField(placeholder, text: $text)
                .textFieldStyle(RoundedBorderTextFieldStyle())
                .disableAutocorrection(true)
                .autocapitalization(.none)
        }
    }
}

@available(iOS 14.0, *)
struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
