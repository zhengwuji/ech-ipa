import SwiftUI

struct ContentView: View {
    // 配置状态
    @State private var serverAddress = "example.com:443"
    @State private var listenAddress = "127.0.0.1:30000"
    @State private var token = ""
    @State private var preferredIP = "saas.sin.fan"
    @State private var dohServer = "dns.alidns.com/dns-query"
    @State private var echDomain = "cloudflare-ech.com"
    @State private var routingMode = 1 // 0=全局, 1=跳过中国大陆, 2=不改变
    
    // UI状态
    @State private var isRunning = false
    @State private var logText = ""
    @State private var showAdvanced = false
    
    // 代理管理器
    @StateObject private var proxyManager = ProxyManager()
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 20) {
                    // 基础配置
                    VStack(alignment: .leading, spacing: 12) {
                        Text("基础配置")
                            .font(.headline)
                            .foregroundColor(.primary)
                        
                        VStack(spacing: 10) {
                            ConfigField(label: "服务地址", text: $serverAddress, placeholder: "example.com:443")
                            ConfigField(label: "监听地址", text: $listenAddress, placeholder: "127.0.0.1:30000")
                            ConfigField(label: "身份令牌", text: $token, placeholder: "可选")
                        }
                    }
                    .padding()
                    .background(Color(.systemBackground))
                    .cornerRadius(12)
                    .shadow(radius: 2)
                    
                    // 高级选项
                    DisclosureGroup("高级选项", isExpanded: $showAdvanced) {
                        VStack(spacing: 10) {
                            ConfigField(label: "优选IP", text: $preferredIP, placeholder: "saas.sin.fan")
                            ConfigField(label: "DOH服务器", text: $dohServer, placeholder: "dns.alidns.com/dns-query")
                            ConfigField(label: "ECH域名", text: $echDomain, placeholder: "cloudflare-ech.com")
                        }
                        .padding(.top, 10)
                    }
                    .padding()
                    .background(Color(.systemBackground))
                    .cornerRadius(12)
                    .shadow(radius: 2)
                    
                    // 代理模式
                    VStack(alignment: .leading, spacing: 12) {
                        Text("代理模式")
                            .font(.headline)
                        
                        Picker("模式", selection: $routingMode) {
                            Text("全局代理").tag(0)
                            Text("跳过中国大陆").tag(1)
                            Text("不改变代理").tag(2)
                        }
                        .pickerStyle(SegmentedPickerStyle())
                    }
                    .padding()
                    .background(Color(.systemBackground))
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
                            .background(isRunning ? Color.gray : Color.green)
                            .foregroundColor(.white)
                            .cornerRadius(10)
                        }
                        .disabled(isRunning)
                        
                        Button(action: stopProxy) {
                            HStack {
                                Image(systemName: "stop.fill")
                                Text("停止代理")
                            }
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(isRunning ? Color.red : Color.gray)
                            .foregroundColor(.white)
                            .cornerRadius(10)
                        }
                        .disabled(!isRunning)
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
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                    }
                    .padding()
                    .background(Color(.systemBackground))
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
                        Text("服务器: 127.0.0.1 端口: 30000")
                            .font(.caption2)
                            .foregroundColor(.blue)
                            .fontWeight(.medium)
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
            appendLog("[系统] ECH Workers 已启动")
            appendLog("[系统] 版本: 1.2.0")
            appendLog("[提示] 配置代理后，在系统设置中手动配置SOCKS5代理")
        }
        .onReceive(proxyManager.$logOutput) { output in
            if !output.isEmpty {
                appendLog(output)
            }
        }
    }
    
    func loadConfig() {
        let defaults = UserDefaults.standard
        serverAddress = defaults.string(forKey: "serverAddress") ?? "example.com:443"
        listenAddress = defaults.string(forKey: "listenAddress") ?? "127.0.0.1:30000"
        token = defaults.string(forKey: "token") ?? ""
        preferredIP = defaults.string(forKey: "preferredIP") ?? "saas.sin.fan"
        dohServer = defaults.string(forKey: "dohServer") ?? "dns.alidns.com/dns-query"
        echDomain = defaults.string(forKey: "echDomain") ?? "cloudflare-ech.com"
        routingMode = defaults.integer(forKey: "routingMode")
    }
    
    func saveConfig() {
        let defaults = UserDefaults.standard
        defaults.set(serverAddress, forKey: "serverAddress")
        defaults.set(listenAddress, forKey: "listenAddress")
        defaults.set(token, forKey: "token")
        defaults.set(preferredIP, forKey: "preferredIP")
        defaults.set(dohServer, forKey: "dohServer")
        defaults.set(echDomain, forKey: "echDomain")
        defaults.set(routingMode, forKey: "routingMode")
        
        appendLog("[系统] 配置已保存")
    }
    
    func startProxy() {
        guard !serverAddress.isEmpty else {
            appendLog("[错误] 请填写服务地址")
            return
        }
        
        saveConfig()
        
        var config = ProxyConfig(
            server: serverAddress,
            listen: listenAddress,
            token: token.isEmpty ? nil : token,
            preferredIP: preferredIP,
            dohServer: dohServer,
            echDomain: echDomain,
            routingMode: routingMode
        )
        
        proxyManager.start(config: config)
        isRunning = true
        appendLog("[系统] 代理已启动")
    }
    
    func stopProxy() {
        proxyManager.stop()
        isRunning = false
        appendLog("[系统] 代理已停止")
    }
    
    func appendLog(_ message: String) {
        let timestamp = DateFormatter.localizedString(from: Date(), dateStyle: .none, timeStyle: .medium)
        logText += "[\(timestamp)] \(message)\n"
    }
}

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
                .autocapitalization(.none)
                .disableAutocorrection(true)
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
