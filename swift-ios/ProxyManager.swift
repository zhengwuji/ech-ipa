import Foundation
import Combine
import Network

struct ProxyConfig {
    let server: String
    let listen: String
    let token: String?
    let preferredIP: String
    let dohServer: String
    let echDomain: String
    let routingMode: Int
}

class ProxyManager: ObservableObject {
    @Published var isRunning = false
    @Published var logOutput = ""
    
    private var listener: NWListener?
    private var connections: [NWConnection] = []
    private var serverHost: String = ""
    private var serverPort: UInt16 = 443
    private var currentConfig: ProxyConfig?
    
    func start(config: ProxyConfig) {
        guard !isRunning else { return }
        
        currentConfig = config
        
        // 解析服务器地址
        let serverParts = config.server.split(separator: ":")
        serverHost = String(serverParts[0])
        serverPort = UInt16(serverParts.count > 1 ? String(serverParts[1]) : "443") ?? 443
        
        // 解析监听地址
        let listenParts = config.listen.split(separator: ":")
        let listenPort = UInt16(listenParts.count > 1 ? String(listenParts[1]) : "30000") ?? 30000
        
        do {
            // 创建 SOCKS5 代理监听器
            let parameters = NWParameters.tcp
            parameters.allowLocalEndpointReuse = true
            
            listener = try NWListener(using: parameters, on: NWEndpoint.Port(rawValue: listenPort)!)
            
            listener?.stateUpdateHandler = { [weak self] state in
                DispatchQueue.main.async {
                    switch state {
                    case .ready:
                        self?.logOutput = "[系统] SOCKS5 代理已启动，监听端口: \(listenPort)"
                        self?.isRunning = true
                    case .failed(let error):
                        self?.logOutput = "[错误] 监听失败: \(error.localizedDescription)"
                        self?.isRunning = false
                    case .cancelled:
                        self?.logOutput = "[系统] 监听已取消"
                        self?.isRunning = false
                    default:
                        break
                    }
                }
            }
            
            listener?.newConnectionHandler = { [weak self] connection in
                self?.handleNewConnection(connection)
            }
            
            listener?.start(queue: .global(qos: .userInitiated))
            
        } catch {
            logOutput = "[错误] 启动失败: \(error.localizedDescription)"
        }
    }
    
    func stop() {
        guard isRunning else { return }
        
        listener?.cancel()
        listener = nil
        
        for connection in connections {
            connection.cancel()
        }
        connections.removeAll()
        
        isRunning = false
        logOutput = "[系统] 代理已停止"
    }
    
    private func handleNewConnection(_ connection: NWConnection) {
        connections.append(connection)
        
        connection.stateUpdateHandler = { [weak self] state in
            switch state {
            case .ready:
                self?.handleSOCKS5Handshake(connection)
            case .failed, .cancelled:
                self?.removeConnection(connection)
            default:
                break
            }
        }
        
        connection.start(queue: .global(qos: .userInitiated))
    }
    
    private func handleSOCKS5Handshake(_ connection: NWConnection) {
        // 接收 SOCKS5 握手请求
        connection.receive(minimumIncompleteLength: 2, maximumLength: 257) { [weak self] data, _, _, error in
            guard let data = data, error == nil else {
                connection.cancel()
                return
            }
            
            // 检查 SOCKS5 版本
            guard data.count >= 2, data[0] == 0x05 else {
                connection.cancel()
                return
            }
            
            // 发送无需认证响应
            let response = Data([0x05, 0x00])
            connection.send(content: response, completion: .contentProcessed { _ in
                self?.handleSOCKS5Request(connection)
            })
        }
    }
    
    private func handleSOCKS5Request(_ connection: NWConnection) {
        // 接收 SOCKS5 连接请求
        connection.receive(minimumIncompleteLength: 4, maximumLength: 512) { [weak self] data, _, _, error in
            guard let self = self, let data = data, error == nil else {
                connection.cancel()
                return
            }
            
            guard data.count >= 4, data[0] == 0x05, data[1] == 0x01 else {
                connection.cancel()
                return
            }
            
            var targetHost: String = ""
            var targetPort: UInt16 = 0
            var offset = 4
            
            // 解析目标地址
            switch data[3] {
            case 0x01: // IPv4
                guard data.count >= 10 else { connection.cancel(); return }
                let ip = "\(data[4]).\(data[5]).\(data[6]).\(data[7])"
                targetHost = ip
                targetPort = UInt16(data[8]) << 8 | UInt16(data[9])
                
            case 0x03: // 域名
                let domainLength = Int(data[4])
                guard data.count >= 5 + domainLength + 2 else { connection.cancel(); return }
                let domainData = data[5..<(5 + domainLength)]
                targetHost = String(data: domainData, encoding: .utf8) ?? ""
                offset = 5 + domainLength
                targetPort = UInt16(data[offset]) << 8 | UInt16(data[offset + 1])
                
            case 0x04: // IPv6
                guard data.count >= 22 else { connection.cancel(); return }
                // 简化处理 IPv6
                connection.cancel()
                return
                
            default:
                connection.cancel()
                return
            }
            
            DispatchQueue.main.async {
                self.logOutput = "[连接] \(targetHost):\(targetPort)"
            }
            
            // 连接到远程服务器（通过我们的代理服务器）
            self.connectToRemote(clientConnection: connection, targetHost: targetHost, targetPort: targetPort)
        }
    }
    
    private func connectToRemote(clientConnection: NWConnection, targetHost: String, targetPort: UInt16) {
        // 使用配置的代理服务器
        let host = NWEndpoint.Host(serverHost)
        let port = NWEndpoint.Port(rawValue: serverPort)!
        
        // 创建 TLS 参数
        let tlsOptions = NWProtocolTLS.Options()
        let tcpOptions = NWProtocolTCP.Options()
        
        let parameters = NWParameters(tls: tlsOptions, tcp: tcpOptions)
        
        let remoteConnection = NWConnection(host: host, port: port, using: parameters)
        
        remoteConnection.stateUpdateHandler = { [weak self] state in
            switch state {
            case .ready:
                // 发送 SOCKS5 成功响应给客户端
                var response = Data([0x05, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00])
                response.append(UInt8(targetPort >> 8))
                response.append(UInt8(targetPort & 0xFF))
                
                clientConnection.send(content: response, completion: .contentProcessed { _ in
                    // 开始双向转发数据
                    self?.startRelaying(client: clientConnection, remote: remoteConnection)
                })
                
            case .failed(let error):
                DispatchQueue.main.async {
                    self?.logOutput = "[错误] 远程连接失败: \(error.localizedDescription)"
                }
                // 发送失败响应
                let response = Data([0x05, 0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                clientConnection.send(content: response, completion: .contentProcessed { _ in
                    clientConnection.cancel()
                })
                
            case .cancelled:
                clientConnection.cancel()
                
            default:
                break
            }
        }
        
        remoteConnection.start(queue: .global(qos: .userInitiated))
    }
    
    private func startRelaying(client: NWConnection, remote: NWConnection) {
        // 客户端 -> 远程
        relayData(from: client, to: remote)
        // 远程 -> 客户端
        relayData(from: remote, to: client)
    }
    
    private func relayData(from source: NWConnection, to destination: NWConnection) {
        source.receive(minimumIncompleteLength: 1, maximumLength: 65536) { [weak self] data, _, isComplete, error in
            if let data = data, !data.isEmpty {
                destination.send(content: data, completion: .contentProcessed { sendError in
                    if sendError == nil {
                        self?.relayData(from: source, to: destination)
                    } else {
                        source.cancel()
                        destination.cancel()
                    }
                })
            }
            
            if isComplete || error != nil {
                source.cancel()
                destination.cancel()
            }
        }
    }
    
    private func removeConnection(_ connection: NWConnection) {
        if let index = connections.firstIndex(where: { $0 === connection }) {
            connections.remove(at: index)
        }
    }
    
    deinit {
        stop()
    }
}
