import Foundation
import Combine

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
    
    private var process: Process?
    private var outputPipe: Pipe?
    
    func start(config: ProxyConfig) {
        guard !isRunning else { return }
        
        // 查找ech-workers二进制文件
        guard let binaryPath = findBinary() else {
            logOutput = "[错误] 未找到ech-workers二进制文件"
            return
        }
        
        // 构建命令参数
        var arguments = [String]()
        arguments.append(contentsOf: ["-f", config.server])
        arguments.append(contentsOf: ["-l", config.listen])
        
        if let token = config.token, !token.isEmpty {
            arguments.append(contentsOf: ["-token", token])
        }
        
        if !config.preferredIP.isEmpty {
            arguments.append(contentsOf: ["-ip", config.preferredIP])
        }
        
        if !config.dohServer.isEmpty && config.dohServer != "dns.alidns.com/dns-query" {
            arguments.append(contentsOf: ["-dns", config.dohServer])
        }
        
        if !config.echDomain.isEmpty && config.echDomain != "cloudflare-ech.com" {
            arguments.append(contentsOf: ["-ech", config.echDomain])
        }
        
        // 创建进程
        process = Process()
        process?.executableURL = URL(fileURLWithPath: binaryPath)
        process?.arguments = arguments
        
        // 设置输出管道
        outputPipe = Pipe()
        process?.standardOutput = outputPipe
        process?.standardError = outputPipe
        
        // 读取输出
        outputPipe?.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            if let output = String(data: data, encoding: .utf8), !output.isEmpty {
                DispatchQueue.main.async {
                    self?.logOutput = output
                }
            }
        }
        
        do {
            try process?.run()
            isRunning = true
            logOutput = "[系统] ech-workers进程已启动"
        } catch {
            logOutput = "[错误] 启动失败: \(error.localizedDescription)"
        }
    }
    
    func stop() {
        guard isRunning else { return }
        
        process?.terminate()
        outputPipe?.fileHandleForReading.readabilityHandler = nil
        
        process = nil
        outputPipe = nil
        isRunning = false
        
        logOutput = "[系统] ech-workers进程已停止"
    }
    
    private func findBinary() -> String? {
        // 尝试多个可能的位置
        let possiblePaths = [
            // App bundle中的资源
            Bundle.main.path(forResource: "ech-workers", ofType: nil),
            Bundle.main.bundlePath + "/ech-workers",
            Bundle.main.resourcePath.map { $0 + "/ech-workers" },
            // 系统路径
            "/usr/local/bin/ech-workers"
        ].compactMap { $0 }
        
        for path in possiblePaths {
            if FileManager.default.isExecutableFile(atPath: path) {
                return path
            }
        }
        
        return nil
    }
    
    deinit {
        stop()
    }
}
