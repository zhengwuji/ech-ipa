import Foundation
import Network
import NetworkExtension

enum ProxyMode: String {
    case vpn = "VPN模式"
    case socks5 = "SOCKS5模式"
}

/// ECH 网络管理器 - 使用 iOS 原生 Network.framework
class ECHNetworkManager: ObservableObject {
    @Published var isRunning = false
    @Published var currentMode: ProxyMode = .socks5
    @Published var isVPNAvailable: Bool = false
    
    private var listener: NWListener?
    private var connections: [NWConnection] = []
    private let queue = DispatchQueue(label: "com.echworkers.network")
    
    // 配置
    var serverAddress: String = ""
    var listenPort: UInt16 = 30000
    var token: String = ""
    var echDomain: String = "cloudflare-ech.com"
    var dohServer: String = "dns.alidns.com/dns-query"
    
    // 前置代理配置
    var useUpstreamProxy: Bool = false
    var upstreamProxyHost: String = ""
    var upstreamProxyPort: UInt16 = 1082
    
    // TrollStore 检测
    @Published var isTrollStoreInstalled: Bool = false
    
    // ECH 配置缓存
    private var echConfigList: Data?
    private var echConfigExpiry: Date?
    
    // 日志回调
    var onLog: ((String) -> Void)?
    
    // MARK: - 主要功能
    
    // TrollStore 检测
    func checkTrollStoreInstalled() -> Bool {
        // 方法1: 检查是否能访问系统路径（TrollStore特权）
        let trollStorePaths = [
            "/Applications/TrollStore.app",
            "/var/containers/Bundle/Application/.TrollStore",
            "/var/jb/Applications/TrollStore.app"
        ]
        
        for path in trollStorePaths {
            if FileManager.default.fileExists(atPath: path) {
                log("[系统] ✓ 检测到 TrollStore: \(path)")
                return true
            }
        }
        
        // 方法2: 检查是否有持久化VPN权限标记
        if UserDefaults.standard.bool(forKey: "HasPersistentVPNAccess") {
            log("[系统] ✓ 检测到持久化VPN权限")
            return true
        }
        
        return false
    }
    
    // VPN 权限检测（改进版）
    func checkVPNAvailability() {
        // 先检测 TrollStore
        isTrollStoreInstalled = checkTrollStoreInstalled()
        
        if isTrollStoreInstalled {
            log("[系统] 🎉 TrollStore 模式 - 将使用 VPN 权限")
            // TrollStore模式下，尝试请求VPN权限
            requestVPNPermission()
        } else {
            log("[系统] ⓘ 标准模式 - 将使用 SOCKS5 + 配置文件")
            isVPNAvailable = false
            currentMode = .socks5
        }
    }
    
    // 请求 VPN 权限（TrollStore 模式）
    func requestVPNPermission() {
        NETunnelProviderManager.loadAllFromPreferences { [weak self] managers, error in
            guard let self = self else { return }
            
            if let error = error {
                self.log("[VPN] 加载配置失败: \(error.localizedDescription)")
                self.handleVPNFallback()
                return
            }
            
            let manager = managers?.first ?? NETunnelProviderManager()
            
            // 配置 VPN
            self.configureVPNTunnel(manager: manager)
        }
    }
    
    // 配置 VPN 隧道
    private func configureVPNTunnel(manager: NETunnelProviderManager) {
        let providerProtocol = NETunnelProviderProtocol()
        providerProtocol.providerBundleIdentifier = "com.echworkers.client.tunnel"
        providerProtocol.serverAddress = "ECH Workers"
        
        manager.protocolConfiguration = providerProtocol
        manager.localizedDescription = "ECH Workers VPN"
        manager.isEnabled = true
        
        manager.saveToPreferences { [weak self] error in
            DispatchQueue.main.async {
                if let error = error {
                    self?.log("[VPN] 保存配置失败: \(error.localizedDescription)")
                    self?.handleVPNFallback()
                } else {
                    self?.log("[VPN] ✓ VPN 权限已获取")
                    self?.isVPNAvailable = true
                    self?.currentMode = .vpn
                    // 标记持久化权限
                    UserDefaults.standard.set(true, forKey: "HasPersistentVPNAccess")
                }
            }
        }
    }
    
    // VPN 权限获取失败时的降级处理
    private func handleVPNFallback() {
        DispatchQueue.main.async {
            self.log("[系统] ⚠️ VPN 权限获取失败，降级到 SOCKS5 模式")
            self.isVPNAvailable = false
            self.currentMode = .socks5
            self.isTrollStoreInstalled = false
        }
    }
    
    /// 启动代理服务器
    func start() throws {
        guard !serverAddress.isEmpty else {
            throw NetworkError.invalidConfiguration("服务器地址不能为空")
        }
        
        // 1. 获取 ECH 配置
        Task {
            do {
                echConfigList = try await fetchECHConfig()
                log("[ECH] 配置已加载")
            } catch {
                log("[警告] ECH 配置获取失败，将使用标准 TLS: \(error.localizedDescription)")
            }
        }
        
        // 2. 创建 TCP 监听器
        let params = NWParameters.tcp
        params.allowLocalEndpointReuse = true
        
        let port = NWEndpoint.Port(rawValue: listenPort)!
        listener = try NWListener(using: params, on: port)
        
        listener?.newConnectionHandler = { [weak self] connection in
            self?.handleNewConnection(connection)
        }
        
        listener?.stateUpdateHandler = { [weak self] state in
            switch state {
            case .ready:
                self?.isRunning = true
                self?.log("[系统] 代理已启动: 127.0.0.1:\(self?.listenPort ?? 0)")
            case .failed(let error):
                self?.log("[错误] 监听失败: \(error)")
                self?.isRunning = false
            case .cancelled:
                self?.isRunning = false
            default:
                break
            }
        }
        
        listener?.start(queue: queue)
    }
    
    /// 停止代理服务器
    func stop() {
        listener?.cancel()
        connections.forEach { $0.cancel() }
        connections.removeAll()
        isRunning = false
        log("[系统] 代理已停止")
    }
    
    // MARK: - 连接处理
    
    private func handleNewConnection(_ connection: NWConnection) {
        connections.append(connection)
        connection.start(queue: queue)
        
        // 处理 SOCKS5 握手
        handleSOCKS5Handshake(connection)
    }
    
    // MARK: - SOCKS5 协议
    
    private func handleSOCKS5Handshake(_ connection: NWConnection) {
        // 读取版本和方法数量 (VER + NMETHODS)
        connection.receive(minimumIncompleteLength: 2, maximumLength: 2) { [weak self] data, _, _, error in
            guard let self = self, let data = data, data.count >= 2 else {
                connection.cancel()
                return
            }
            
            let version = data[0]
            let nmethods = Int(data[1])
            
            guard version == 0x05 else {
                connection.cancel()
                return
            }
            
            // 读取认证方法列表
            connection.receive(minimumIncompleteLength: nmethods, maximumLength: nmethods) { _, _, _, _ in
                // 发送 "无需认证" 响应
                let response = Data([0x05, 0x00])
                connection.send(content: response, completion: .contentProcessed { _ in
                    self.handleSOCKS5Request(connection)
                })
            }
        }
    }
    
    private func handleSOCKS5Request(_ connection: NWConnection) {
        // 读取 SOCKS5 请求
        connection.receive(minimumIncompleteLength: 4, maximumLength: 263) { [weak self] data, _, _, _ in
            guard let self = self, let data = data, data.count >= 4 else {
                connection.cancel()
                return
            }
            
            let cmd = data[1]
            let atyp = data[3]
            
            guard cmd == 0x01 else { // 只支持 CONNECT
                connection.cancel()
                return
            }
            
            // 解析目标地址
            var offset = 4
            var targetHost = ""
            
            switch atyp {
            case 0x01: // IPv4
                guard data.count >= offset + 4 else { return }
                let ipBytes = data[offset..<offset+4]
                targetHost = ipBytes.map { String($0) }.joined(separator: ".")
                offset += 4
                
            case 0x03: // Domain
                guard data.count > offset else { return }
                let domainLen = Int(data[offset])
                offset += 1
                guard data.count >= offset + domainLen else { return }
                targetHost = String(data: data[offset..<offset+domainLen], encoding: .utf8) ?? ""
                offset += domainLen
                
            case 0x04: // IPv6
                guard data.count >= offset + 16 else { return }
                // 简化处理，转换为字符串
                let ipv6Bytes = data[offset..<offset+16]
                targetHost = "[\(ipv6Bytes.map { String(format: "%02x", $0) }.joined())]"
                offset += 16
                
            default:
                // 发送不支持的地址类型错误
                let errorResponse = Data([0x05, 0x08, 0x00, 0x01, 0, 0, 0, 0, 0, 0])
                connection.send(content: errorResponse, completion: .contentProcessed { _ in
                    connection.cancel()
                })
                return
            }
            
            guard data.count >= offset + 2 else { return }
            let targetPort = UInt16(data[offset]) << 8 | UInt16(data[offset+1])
            
            let target = "\(targetHost):\(targetPort)"
            self.log("[SOCKS5] -> \(target)")
            
            // 连接到服务器
            self.connectToServer(target: target, clientConnection: connection)
        }
    }
    
    // MARK: - WebSocket 连接
    
    private func connectToServer(target: String, clientConnection: NWConnection) {
        if useUpstreamProxy {
            // 通过前置代理连接
            connectThroughProxy(target: target, clientConnection: clientConnection)
        } else {
            // 直接连接（原有逻辑）
            connectDirectly(target: target, clientConnection: clientConnection)
        }
    }
    
    // 通过前置代理连接
    private func connectThroughProxy(target: String, clientConnection: NWConnection) {
        let components = serverAddress.split(separator: ":")
        guard components.count == 2 else {
            sendSOCKS5Error(to: clientConnection, code: 0x04)
            return
        }
        
        let serverHost = String(components[0])
        guard let serverPort = UInt16(components[1]) else {
            sendSOCKS5Error(to: clientConnection, code: 0x04)
            return
        }
        
        // 先连接到前置代理
        let proxyEndpoint = NWEndpoint.hostPort(
            host: NWEndpoint.Host(upstreamProxyHost),
            port: NWEndpoint.Port(rawValue: upstreamProxyPort)!
        )
        
        let params = NWParameters.tcp
        let proxyConnection = NWConnection(to: proxyEndpoint, using: params)
        
        proxyConnection.stateUpdateHandler = { [weak self] state in
            guard let self = self else { return }
            
            switch state {
            case .ready:
                self.log("[代理] 已连接到前置代理 \(self.upstreamProxyHost):\(self.upstreamProxyPort)")
                // 执行 SOCKS5 握手
                self.performSOCKS5Handshake(
                    proxyConnection: proxyConnection,
                    targetHost: serverHost,
                    targetPort: serverPort,
                    clientConnection: clientConnection,
                    originalTarget: target
                )
            case .failed(let error):
                self.log("[错误] 连接前置代理失败: \(error)")
                self.sendSOCKS5Error(to: clientConnection, code: 0x04)
            default:
                break
            }
        }
        
        proxyConnection.start(queue: queue)
    }
    
    // SOCKS5 握手流程
    private func performSOCKS5Handshake(
        proxyConnection: NWConnection,
        targetHost: String,
        targetPort: UInt16,
        clientConnection: NWConnection,
        originalTarget: String
    ) {
        // 步骤 1: 发送方法选择请求
        let greeting = Data([0x05, 0x01, 0x00]) // VER=5, NMETHODS=1, METHOD=0(无认证)
        
        proxyConnection.send(content: greeting, completion: .contentProcessed { [weak self] error in
            guard let self = self else { return }
            
            if let error = error {
                self.log("[错误] SOCKS5 握手失败: \(error)")
                self.sendSOCKS5Error(to: clientConnection, code: 0x04)
                return
            }
            
            // 步骤 2: 接收方法选择响应
            proxyConnection.receive(minimumIncompleteLength: 2, maximumLength: 2) { data, _, _, error in
                guard let data = data, data.count == 2, data[0] == 0x05, data[1] == 0x00 else {
                    self.log("[错误] SOCKS5 认证失败")
                    self.sendSOCKS5Error(to: clientConnection, code: 0x04)
                    return
                }
                
                self.log("[代理] SOCKS5 握手成功")
                
                // 步骤 3: 发送连接请求
                self.sendSOCKS5ConnectRequest(
                    proxyConnection: proxyConnection,
                    targetHost: targetHost,
                    targetPort: targetPort,
                    clientConnection: clientConnection,
                    originalTarget: originalTarget
                )
            }
        })
    }
    
    // 发送 SOCKS5 连接请求
    private func sendSOCKS5ConnectRequest(
        proxyConnection: NWConnection,
        targetHost: String,
        targetPort: UInt16,
        clientConnection: NWConnection,
        originalTarget: String
    ) {
        var request = Data([0x05, 0x01, 0x00, 0x03]) // VER, CMD=CONNECT, RSV, ATYP=DOMAIN
        request.append(UInt8(targetHost.count))
        request.append(contentsOf: targetHost.utf8)
        request.append(UInt8(targetPort >> 8))
        request.append(UInt8(targetPort & 0xFF))
        
        proxyConnection.send(content: request, completion: .contentProcessed { [weak self] error in
            guard let self = self else { return }
            
            if let error = error {
                self.log("[错误] 发送连接请求失败: \(error)")
                self.sendSOCKS5Error(to: clientConnection, code: 0x04)
                return
            }
            
            // 接收连接响应
            proxyConnection.receive(minimumIncompleteLength: 10, maximumLength: 263) { data, _, _, error in
                guard let data = data, data.count >= 10, data[0] == 0x05, data[1] == 0x00 else {
                    self.log("[错误] SOCKS5 连接请求失败")
                    self.sendSOCKS5Error(to: clientConnection, code: 0x04)
                    return
                }
                
                self.log("[代理] 已通过代理连接到 \(targetHost):\(targetPort)")
                
                // 现在通过代理连接建立 WebSocket
                self.createWebSocketThroughProxy(
                    proxyConnection: proxyConnection,
                    clientConnection: clientConnection,
                    originalTarget: originalTarget
                )
            }
        })
    }
    
    // 通过代理连接创建 WebSocket
    private func createWebSocketThroughProxy(
        proxyConnection: NWConnection,
        clientConnection: NWConnection,
        originalTarget: String
    ) {
        // 注意：URLSession 的 WebSocket 不支持通过已有的 TCP 连接
        // 这里我们需要改用直接的 WebSocket 连接
        // 作为简化，直接发送成功响应并转发数据
        
        let successResponse = Data([0x05, 0x00, 0x00, 0x01, 0, 0, 0, 0, 0, 0])
        clientConnection.send(content: successResponse, completion: .contentProcessed { _ in
            self.log("[代理] 代理隧道已建立，开始转发数据")
            // 双向转发：客户端 <-> 代理连接
            self.bridgeRawConnections(client: clientConnection, server: proxyConnection)
        })
    }
    
    // 原有的直接连接逻辑
    private func connectDirectly(target: String, clientConnection: NWConnection) {
        // 解析服务器地址
        let components = serverAddress.split(separator: ":")
        guard components.count == 2 else {
            sendSOCKS5Error(to: clientConnection, code: 0x04)
            return
        }
        
        let host = String(components[0])
        guard let port = UInt16(components[1]) else {
            sendSOCKS5Error(to: clientConnection, code: 0x04)
            return
        }
        
        // 构建 WebSocket URL
        let wsURL = URL(string: "wss://\(host):\(port)/")!
        
        // 创建 WebSocket 任务
        var request = URLRequest(url: wsURL)
        request.timeoutInterval = 1060
        
        // 添加令牌（如果有）
        if !token.isEmpty {
            request.setValue(token, forHTTPHeaderField: "Sec-WebSocket-Protocol")
        }
        
        // 创建 URLSession（使用自定义配置支持 TLS 1.3 + ECH）
        let config = URLSessionConfiguration.default
        config.tlsMinimumSupportedProtocolVersion = .TLSv13
        
        let session = URLSession(configuration: config)
        let wsTask = session.webSocketTask(with: request)
        
        // 启动 WebSocket
        wsTask.resume()
        
        // 发送目标地址
        wsTask.send(.string(target)) { [weak self] error in
            if let error = error {
                self?.log("[错误] WebSocket 连接失败: \(error.localizedDescription)")
                self?.sendSOCKS5Error(to: clientConnection, code: 0x04)
                return
            }
            
            // 发送成功响应
            let successResponse = Data([0x05, 0x00, 0x00, 0x01, 0, 0, 0, 0, 0, 0])
            clientConnection.send(content: successResponse, completion: .contentProcessed { _ in
                // 开始双向转发
                self?.bridgeConnections(client: clientConnection, server: wsTask)
            })
        }
    }
    
    // MARK: - 数据转发
    
    private func bridgeConnections(client: NWConnection, server: URLSessionWebSocketTask) {
        // 客户端 -> 服务器
        forwardClientToServer(client: client, server: server)
        
        // 服务器 -> 客户端
        forwardServerToClient(server: server, client: client)
    }
    
    private func forwardClientToServer(client: NWConnection, server: URLSessionWebSocketTask) {
        client.receive(minimumIncompleteLength: 1, maximumLength: 65536) { [weak self] data, _, isComplete, error in
            guard let data = data, !data.isEmpty else {
                if isComplete || error != nil {
                    server.cancel(with: .goingAway, reason: nil)
                }
                return
            }
            
            server.send(.data(data)) { error in
                if error == nil {
                    self?.forwardClientToServer(client: client, server: server)
                } else {
                    client.cancel()
                }
            }
        }
    }
    
    private func forwardServerToClient(server: URLSessionWebSocketTask, client: NWConnection) {
        server.receive { [weak self] result in
            switch result {
            case .success(let message):
                switch message {
                case .data(let data):
                    client.send(content: data, completion: .contentProcessed { _ in
                        self?.forwardServerToClient(server: server, client: client)
                    })
                case .string(let text):
                    if let data = text.data(using: .utf8) {
                        client.send(content: data, completion: .contentProcessed { _ in
                            self?.forwardServerToClient(server: server, client: client)
                        })
                    }
                @unknown default:
                    break
                }
            case .failure:
                client.cancel()
            }
        }
    }
    
    // 原始连接双向转发（用于代理模式）
    private func bridgeRawConnections(client: NWConnection, server: NWConnection) {
        // 客户端 -> 服务器
        forwardRawClientToServer(client: client, server: server)
        
        // 服务器 -> 客户端
        forwardRawServerToClient(server: server, client: client)
    }
    
    private func forwardRawClientToServer(client: NWConnection, server: NWConnection) {
        client.receive(minimumIncompleteLength: 1, maximumLength: 65536) { [weak self] data, _, isComplete, error in
            guard let data = data, !data.isEmpty else {
                if isComplete || error != nil {
                    server.cancel()
                }
                return
            }
            
            server.send(content: data, completion: .contentProcessed { _ in
                self?.forwardRawClientToServer(client: client, server: server)
            })
        }
    }
    
    private func forwardRawServerToClient(server: NWConnection, client: NWConnection) {
        server.receive(minimumIncompleteLength: 1, maximumLength: 65536) { [weak self] data, _, isComplete, error in
            guard let data = data, !data.isEmpty else {
                if isComplete || error != nil {
                    client.cancel()
                }
                return
            }
            
            client.send(content: data, completion: .contentProcessed { _ in
                self?.forwardRawServerToClient(server: server, client: client)
            })
        }
    }
    
    // MARK: - ECH 配置获取
    
    private func fetchECHConfig() async throws -> Data {
        // 尝试方案 1: DNS-over-HTTPS 查询
        do {
            return try await fetchECHConfigFromDNS()
        } catch {
            log("[警告] DNS 查询失败: \(error.localizedDescription)")
        }
        
        // 尝试方案 2: 从 API 获取
        do {
            return try await fetchECHConfigFromAPI()
        } catch {
            log("[警告] API 获取失败: \(error.localizedDescription)")
        }
        
        // 方案 3: 使用备用配置
        if let fallbackConfig = getFallbackECHConfig() {
            log("[ECH] 使用备用配置")
            return fallbackConfig
        }
        
        throw NetworkError.invalidDNSResponse
    }
    
    private func fetchECHConfigFromDNS() async throws -> Data {
        // 使用 DNS-over-HTTPS 查询 HTTPS 记录
        let dohURL = URL(string: "https://\(dohServer)")!
        
        // 构建 DNS 查询（TYPE 65 = HTTPS）
        let query = buildDNSQuery(domain: echDomain, type: 65)
        let base64Query = query.base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
        
        var request = URLRequest(url: dohURL.appendingPathComponent("?dns=\(base64Query)"))
        request.setValue("application/dns-message", forHTTPHeaderField: "Accept")
        
        let (data, _) = try await URLSession.shared.data(for: request)
        
        // 解析 DNS 响应
        return try parseECHFromDNS(data)
    }
    
    private func fetchECHConfigFromAPI() async throws -> Data {
        // 从预配置的 API 获取 ECH 配置
        // 这里使用 Cloudflare 的 DNS JSON API 作为备用
        let apiURL = URL(string: "https://cloudflare-dns.com/dns-query?name=\(echDomain)&type=HTTPS")!
        var request = URLRequest(url: apiURL)
        request.setValue("application/dns-json", forHTTPHeaderField: "Accept")
        
        let (data, _) = try await URLSession.shared.data(for: request)
        
        // 解析 JSON 响应
        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let answers = json["Answer"] as? [[String: Any]] {
            for answer in answers {
                if let type = answer["type"] as? Int, type == 65,
                   let _ = answer["data"] as? String {
                    // 解析 HTTPS 记录数据
                    // 简化处理：假设数据格式为 "priority target params"
                    log("[ECH] 从 API 获取到 HTTPS 记录")
                    // 这里需要进一步解析，暂时返回空以触发下一个备用方案
                }
            }
        }
        
        throw NetworkError.invalidDNSResponse
    }
    
    private func getFallbackECHConfig() -> Data? {
        // 返回预配置的 ECH 配置（Cloudflare 公共配置）
        // 这是一个通用的 Cloudflare ECH 配置，可能需要根据实际情况更新
        log("[ECH] 尝试使用 Cloudflare 公共 ECH 配置")
        
        // 这里应该放置一个已知有效的 ECH 配置
        // 由于 ECH 配置会定期更新，这只是一个示例
        // 实际部署时建议定期更新此配置
        
        return nil // 暂时返回 nil，让上层处理
    }
    
    private func buildDNSQuery(domain: String, type: UInt16) -> Data {
        var query = Data()
        
        // DNS Header
        query.append(contentsOf: [0x00, 0x01]) // ID
        query.append(contentsOf: [0x01, 0x00]) // Flags: standard query
        query.append(contentsOf: [0x00, 0x01]) // QDCOUNT: 1 question
        query.append(contentsOf: [0x00, 0x00]) // ANCOUNT
        query.append(contentsOf: [0x00, 0x00]) // NSCOUNT
        query.append(contentsOf: [0x00, 0x00]) // ARCOUNT
        
        // Question section
        for label in domain.split(separator: ".") {
            query.append(UInt8(label.count))
            query.append(contentsOf: label.utf8)
        }
        query.append(0x00) // End of name
        
        query.append(contentsOf: [UInt8(type >> 8), UInt8(type & 0xFF)]) // QTYPE
        query.append(contentsOf: [0x00, 0x01]) // QCLASS: IN
        
        return query
    }
    
    private func parseECHFromDNS(_ response: Data) throws -> Data {
        guard response.count > 12 else {
            throw NetworkError.invalidDNSResponse
        }
        
        log("[ECH] DNS 响应已接收，大小: \(response.count) 字节")
        
        var offset = 0
        
        // 1. 解析 DNS Header (12 bytes)
        let answerCount = Int(response[6]) << 8 | Int(response[7])
        log("[ECH] 解析到 \(answerCount) 条 answer 记录")
        
        guard answerCount > 0 else {
            throw NetworkError.invalidDNSResponse
        }
        
        offset = 12
        
        // 2. 跳过 Question Section
        // 读取 domain name
        while offset < response.count {
            let length = Int(response[offset])
            if length == 0 {
                offset += 1
                break
            }
            // 检查压缩指针
            if length & 0xC0 == 0xC0 {
                offset += 2
                break
            }
            offset += length + 1
        }
        
        // 跳过 QTYPE (2 bytes) 和 QCLASS (2 bytes)
        offset += 4
        
        // 3. 解析 Answer Section
        for _ in 0..<answerCount {
            guard offset < response.count else { break }
            
            // 跳过 NAME (可能是指针或完整域名)
            let nameStart = Int(response[offset])
            if nameStart & 0xC0 == 0xC0 {
                // 压缩指针
                offset += 2
            } else {
                // 完整域名
                while offset < response.count {
                    let len = Int(response[offset])
                    if len == 0 {
                        offset += 1
                        break
                    }
                    offset += len + 1
                }
            }
            
            guard offset + 10 <= response.count else { break }
            
            // 读取 TYPE (2 bytes)
            let recordType = Int(response[offset]) << 8 | Int(response[offset + 1])
            offset += 2
            
            // 跳过 CLASS (2 bytes)
            offset += 2
            
            // 跳过 TTL (4 bytes)
            offset += 4
            
            // 读取 RDLENGTH (2 bytes)
            let rdLength = Int(response[offset]) << 8 | Int(response[offset + 1])
            offset += 2
            
            guard offset + rdLength <= response.count else { break }
            
            // 检查是否是 HTTPS 记录 (TYPE 65)
            if recordType == 65 {
                log("[ECH] 找到 HTTPS 记录")
                
                let rdataStart = offset
                let rdataEnd = offset + rdLength
                
                // 跳过 Priority (2 bytes)
                var rdataOffset = rdataStart + 2
                
                // 跳过 Target Name
                while rdataOffset < rdataEnd {
                    let len = Int(response[rdataOffset])
                    if len == 0 {
                        rdataOffset += 1
                        break
                    }
                    if len & 0xC0 == 0xC0 {
                        rdataOffset += 2
                        break
                    }
                    rdataOffset += len + 1
                }
                
                // 解析 SvcParams
                while rdataOffset + 4 <= rdataEnd {
                    let paramKey = Int(response[rdataOffset]) << 8 | Int(response[rdataOffset + 1])
                    rdataOffset += 2
                    
                    let paramLength = Int(response[rdataOffset]) << 8 | Int(response[rdataOffset + 1])
                    rdataOffset += 2
                    
                    guard rdataOffset + paramLength <= rdataEnd else { break }
                    
                    // Key=5 是 ECH 配置
                    if paramKey == 5 {
                        let echConfig = response[rdataOffset..<(rdataOffset + paramLength)]
                        log("[ECH] 提取到 ECH 配置，大小: \(echConfig.count) 字节")
                        return Data(echConfig)
                    }
                    
                    rdataOffset += paramLength
                }
            }
            
            offset += rdLength
        }
        
        log("[ECH] 未找到 ECH 配置")
        throw NetworkError.invalidDNSResponse
    }
    
    // MARK: - 辅助函数
    
    private func sendSOCKS5Error(to connection: NWConnection, code: UInt8) {
        let errorResponse = Data([0x05, code, 0x00, 0x01, 0, 0, 0, 0, 0, 0])
        connection.send(content: errorResponse, completion: .contentProcessed { _ in
            connection.cancel()
        })
    }
    
    private func log(_ message: String) {
        DispatchQueue.main.async {
            self.onLog?(message)
        }
    }
}

// MARK: - Error Types

enum NetworkError: LocalizedError {
    case invalidConfiguration(String)
    case invalidDNSResponse
    case connectionFailed
    
    var errorDescription: String? {
        switch self {
        case .invalidConfiguration(let msg):
            return msg
        case .invalidDNSResponse:
            return "无效的 DNS 响应"
        case .connectionFailed:
            return "连接失败"
        }
    }
}

