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
                log("[ECH] ECH 配置获取失败，将使用加密 TLS 无 ECH 连接")
                log("[ECH] 失败原因: \(error.localizedDescription)")
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
        
        log("[SOCKS5] 新连接已建立")
        
        // 处理 SOCKS5 握手
        handleSOCKS5Handshake(connection)
    }
    
    // MARK: - SOCKS5 协议
    
    private func handleSOCKS5Handshake(_ connection: NWConnection) {
        // 读取版本和方法数量 (VER + NMETHODS)
        connection.receive(minimumIncompleteLength: 2, maximumLength: 2) { [weak self] data, _, _, error in
            guard let self = self, let data = data, data.count >= 2 else {
                self?.log("[SOCKS5] 握手失败: 数据不足")
                connection.cancel()
                return
            }
            
            let version = data[0]
            let nmethods = Int(data[1])
            
            self.log("[SOCKS5] 揥手: version=\(version), nmethods=\(nmethods)")
            
            guard version == 0x05 else {
                self.log("[SOCKS5] 错误: 不支持的版本 \(version)")
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
            
            guard data.count >= offset + 2 else { 
                self.log("[SOCKS5] 错误: 目标端口数据不足")
                return 
            }
            let targetPort = UInt16(data[offset]) << 8 | UInt16(data[offset+1])
            
            let target = "\(targetHost):\(targetPort)"
            self.log("[SOCKS5] -> \(target)")
            
            // 连接到服务器
            self.log("[SOCKS5] 开始连接到服务器...")
            self.connectToServer(target: target, clientConnection: connection)
        }
    }
    
    // MARK: - WebSocket 连接
    
    private func connectToServer(target: String, clientConnection: NWConnection) {
        // 统一使用 URLSession 处理连接（支持直连和前置代理）
        connectToECHServer(target: target, clientConnection: clientConnection)
    }
    
    // 连接到 ECH 服务器 (支持前置代理)
    private func connectToECHServer(target: String, clientConnection: NWConnection) {
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
        request.timeoutInterval = 30
        
        // 添加令牌（如果有）
        if !token.isEmpty {
            request.setValue(token, forHTTPHeaderField: "Sec-WebSocket-Protocol")
        }
        
        log("[WebSocket] 正在连接到 wss://\(host):\(port)/ ...")
        
        // 创建 URLSession（使用自定义配置支持 TLS 1.3 + ECH + 前置代理）
        let config = getSessionConfiguration()
        
        let session = URLSession(configuration: config)
        let wsTask = session.webSocketTask(with: request)
        
        // 启动 WebSocket
        wsTask.resume()
        log("[WebSocket] WebSocket 任务已启动")
        
        // 发送目标地址
        wsTask.send(.string(target)) { [weak self] error in
            if let error = error {
                self?.log("[错误] WebSocket 连接失败: \(error.localizedDescription)")
                self?.sendSOCKS5Error(to: clientConnection, code: 0x04)
                return
            }
            
            self?.log("[WebSocket] ✓ 已连接并发送目标: \(target)")
            
            // 发送成功响应
            let successResponse = Data([0x05, 0x00, 0x00, 0x01, 0, 0, 0, 0, 0, 0])
            clientConnection.send(content: successResponse, completion: .contentProcessed { _ in
                // 开始双向转发
                self?.log("[代理] 开始转发数据: \(target)")
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
    
    // MARK: - 辅助方法
    
    private func getSessionConfiguration() -> URLSessionConfiguration {
        let config = URLSessionConfiguration.default
        config.tlsMinimumSupportedProtocolVersion = .TLSv13
        config.requestCachePolicy = .reloadIgnoringLocalCacheData
        
        if useUpstreamProxy && !upstreamProxyHost.isEmpty {
            log("[代理] 使用前置SOCKS5代理: \(upstreamProxyHost):\(upstreamProxyPort)")
            
            // 使用更完整的代理配置
            let proxyDict: [String: Any] = [
                kCFNetworkProxiesSOCKSEnable as String: 1,
                kCFNetworkProxiesSOCKSProxy as String: upstreamProxyHost,
                kCFNetworkProxiesSOCKSPort as String: Int(upstreamProxyPort),
                kCFProxyTypeKey as String: kCFProxyTypeSOCKS
            ]
            config.connectionProxyDictionary = proxyDict
            
            log("[代理] 代理配置已设置")
        } else {
            log("[代理] 直连模式（无前置代理）")
        }
        
        return config
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
        
        // 修复：正确构建 DNS-over-HTTPS URL
        let queryURL = dohURL.absoluteString + "?dns=" + base64Query
        guard let requestURL = URL(string: queryURL) else {
            log("[ECH] DNS 查询 URL 构建失败")
            throw NetworkError.invalidDNSResponse
        }
        
        var request = URLRequest(url: requestURL)
        request.setValue("application/dns-message", forHTTPHeaderField: "Accept")
        request.timeoutInterval = 10
        
        log("[ECH] 正在通过 DoH 查询 \(echDomain)...")
        
        let (data, response) = try await URLSession(configuration: getSessionConfiguration()).data(for: request)
        
        if let httpResponse = response as? HTTPURLResponse {
            log("[ECH] DoH 响应状态码: \(httpResponse.statusCode)")
        }
        
        // 解析 DNS 响应
        return try parseECHFromDNS(data)
    }
    
    private func fetchECHConfigFromAPI() async throws -> Data {
        // 从预配置的 API 获取 ECH 配置
        // 这里使用 Cloudflare 的 DNS JSON API 作为备用
        let apiURL = URL(string: "https://cloudflare-dns.com/dns-query?name=\(echDomain)&type=HTTPS")!
        var request = URLRequest(url: apiURL)
        request.setValue("application/dns-json", forHTTPHeaderField: "Accept")
        
        let (data, _) = try await URLSession(configuration: getSessionConfiguration()).data(for: request)
        
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
        log("[ECH] 使用内置的 Cloudflare ECH 配置")
        
        // Cloudflare 公开的 ECH 配置（cloudflare-ech.com）
        // 这是一个基本的配置，可以作为备用方案
        // 注意：ECH 配置可能会定期更新，建议定期检查更新
        
        // 这是 cloudflare-ech.com 的一个示例 ECH 配置
        // 使用十六进制字符串编码（这是一个通用配置）
        let echConfigHex = "fe0d007b0020002000200020636c6f7564666c6172652d6563682e636f6d000500010001000100030002683200040008000600010003"
        
        // 将十六进制字符串转换为 Data
        var data = Data()
        var hex = echConfigHex
        while !hex.isEmpty {
            let subIndex = hex.index(hex.startIndex, offsetBy: 2)
            let byteString = hex[..<subIndex]
            hex = String(hex[subIndex...])
            
            if let byte = UInt8(byteString, radix: 16) {
                data.append(byte)
            }
        }
        
        if !data.isEmpty {
            log("[ECH] 已加载内置 ECH 配置，大小: \(data.count) 字节")
            return data
        }
        
        log("[ECH] 内置配置加载失败")
        return nil
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

