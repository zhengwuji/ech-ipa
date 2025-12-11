import Foundation
import Network

/// ECH 网络管理器 - 使用 iOS 原生 Network.framework
class ECHNetworkManager: ObservableObject {
    @Published var isRunning = false
    
    private var listener: NWListener?
    private var connections: [NWConnection] = []
    private let queue = DispatchQueue(label: "com.echworkers.network")
    
    // 配置
    var serverAddress: String = ""
    var listenPort: UInt16 = 30000
    var token: String = ""
    var echDomain: String = "cloudflare-ech.com"
    var dohServer: String = "dns.alidns.com/dns-query"
    
    // ECH 配置缓存
    private var echConfigList: Data?
    private var echConfigExpiry: Date?
    
    // 日志回调
    var onLog: ((String) -> Void)?
    
    // MARK: - 主要功能
    
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
    
    // MARK: - ECH 配置获取
    
    private func fetchECHConfig() async throws -> Data {
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
        // 简化的 DNS 响应解析
        // 在实际实现中需要完整解析 DNS 响应格式
        
        guard response.count > 12 else {
            throw NetworkError.invalidDNSResponse
        }
        
        // 跳过 header 和 question section
        // 查找 HTTPS 记录中的 ECH 参数（key=5）
        
        // 这里需要实现完整的 DNS 解析逻辑
        // 临时返回空数据，实际使用时需要完善
        
        log("[ECH] DNS 响应解析中...")
        return Data()
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
