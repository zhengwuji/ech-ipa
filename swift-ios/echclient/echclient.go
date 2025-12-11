package echclient

import (
	"bytes"
	"context"
	"crypto/tls"
	"crypto/x509"
	"encoding/base64"
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"reflect"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// ECHClient 是提供给 iOS 调用的主客户端
type ECHClient struct {
	listenAddr string
	serverAddr string
	serverIP   string
	token      string
	dnsServer  string
	echDomain  string
	
	echListMu sync.RWMutex
	echList   []byte
	
	listener  net.Listener
	running   bool
	stopChan  chan struct{}
	logFunc   func(string)
}

// NewECHClient 创建新的 ECH 客户端
func NewECHClient() *ECHClient {
	return &ECHClient{
		listenAddr: "127.0.0.1:30000",
		dnsServer:  "dns.alidns.com/dns-query",
		echDomain:  "cloudflare-ech.com",
	}
}

// SetLogCallback 设置日志回调
func (c *ECHClient) SetLogCallback(callback func(string)) {
	c.logFunc = callback
}

func (c *ECHClient) log(format string, args ...interface{}) {
	msg := fmt.Sprintf(format, args...)
	if c.logFunc != nil {
		c.logFunc(msg)
	}
	log.Print(msg)
}

// Configure 配置客户端
func (c *ECHClient) Configure(serverAddr, listenAddr, token, serverIP, dnsServer, echDomain string) {
	c.serverAddr = serverAddr
	if listenAddr != "" {
		c.listenAddr = listenAddr
	}
	c.token = token
	c.serverIP = serverIP
	if dnsServer != "" {
		c.dnsServer = dnsServer
	}
	if echDomain != "" {
		c.echDomain = echDomain
	}
}

// Start 启动代理服务器
func (c *ECHClient) Start() error {
	if c.running {
		return errors.New("代理已在运行")
	}
	
	if c.serverAddr == "" {
		return errors.New("未配置服务器地址")
	}
	
	c.log("[启动] 正在获取 ECH 配置...")
	if err := c.prepareECH(); err != nil {
		return fmt.Errorf("获取 ECH 配置失败: %w", err)
	}
	
	listener, err := net.Listen("tcp", c.listenAddr)
	if err != nil {
		return fmt.Errorf("监听失败: %w", err)
	}
	
	c.listener = listener
	c.running = true
	c.stopChan = make(chan struct{})
	
	c.log("[代理] 服务器启动: %s", c.listenAddr)
	c.log("[代理] 后端服务器: %s", c.serverAddr)
	
	go c.acceptLoop()
	
	return nil
}

// Stop 停止代理服务器
func (c *ECHClient) Stop() {
	if !c.running {
		return
	}
	
	close(c.stopChan)
	if c.listener != nil {
		c.listener.Close()
	}
	c.running = false
	c.log("[代理] 已停止")
}

// IsRunning 返回运行状态
func (c *ECHClient) IsRunning() bool {
	return c.running
}

func (c *ECHClient) acceptLoop() {
	for {
		select {
		case <-c.stopChan:
			return
		default:
		}
		
		conn, err := c.listener.Accept()
		if err != nil {
			select {
			case <-c.stopChan:
				return
			default:
				continue
			}
		}
		
		go c.handleConnection(conn)
	}
}

func (c *ECHClient) handleConnection(conn net.Conn) {
	defer conn.Close()
	
	conn.SetDeadline(time.Now().Add(30 * time.Second))
	
	buf := make([]byte, 1)
	n, err := conn.Read(buf)
	if err != nil || n == 0 {
		return
	}
	
	firstByte := buf[0]
	
	switch firstByte {
	case 0x05:
		c.handleSOCKS5(conn, firstByte)
	default:
		c.log("[代理] 未知协议: 0x%02x", firstByte)
	}
}

// ======================== ECH 支持 ========================

const typeHTTPS = 65

func (c *ECHClient) prepareECH() error {
	echBase64, err := c.queryHTTPSRecord(c.echDomain, c.dnsServer)
	if err != nil {
		return fmt.Errorf("DNS 查询失败: %w", err)
	}
	if echBase64 == "" {
		return errors.New("未找到 ECH 参数")
	}
	raw, err := base64.StdEncoding.DecodeString(echBase64)
	if err != nil {
		return fmt.Errorf("ECH 解码失败: %w", err)
	}
	c.echListMu.Lock()
	c.echList = raw
	c.echListMu.Unlock()
	c.log("[ECH] 配置已加载，长度: %d 字节", len(raw))
	return nil
}

func (c *ECHClient) getECHList() ([]byte, error) {
	c.echListMu.RLock()
	defer c.echListMu.RUnlock()
	if len(c.echList) == 0 {
		return nil, errors.New("ECH 配置未加载")
	}
	return c.echList, nil
}

func (c *ECHClient) buildTLSConfigWithECH(serverName string, echList []byte) (*tls.Config, error) {
	roots, err := x509.SystemCertPool()
	if err != nil {
		return nil, fmt.Errorf("加载系统根证书失败: %w", err)
	}

	if echList == nil || len(echList) == 0 {
		return nil, errors.New("ECH 配置为空")
	}

	config := &tls.Config{
		MinVersion: tls.VersionTLS13,
		ServerName: serverName,
		RootCAs:    roots,
	}

	if err := setECHConfig(config, echList); err != nil {
		return nil, fmt.Errorf("设置 ECH 配置失败: %w", err)
	}

	return config, nil
}

func setECHConfig(config *tls.Config, echList []byte) error {
	configValue := reflect.ValueOf(config).Elem()

	field1 := configValue.FieldByName("EncryptedClientHelloConfigList")
	if !field1.IsValid() || !field1.CanSet() {
		return fmt.Errorf("EncryptedClientHelloConfigList 字段不可用")
	}
	field1.Set(reflect.ValueOf(echList))

	field2 := configValue.FieldByName("EncryptedClientHelloRejectionVerify")
	if !field2.IsValid() || !field2.CanSet() {
		return fmt.Errorf("EncryptedClientHelloRejectionVerify 字段不可用")
	}
	rejectionFunc := func(cs tls.ConnectionState) error {
		return errors.New("服务器拒绝 ECH")
	}
	field2.Set(reflect.ValueOf(rejectionFunc))

	return nil
}

func (c *ECHClient) queryHTTPSRecord(domain, dnsServer string) (string, error) {
	dohURL := dnsServer
	if !strings.HasPrefix(dohURL, "https://") && !strings.HasPrefix(dohURL, "http://") {
		dohURL = "https://" + dohURL
	}
	return c.queryDoH(domain, dohURL)
}

func (c *ECHClient) queryDoH(domain, dohURL string) (string, error) {
	u, err := url.Parse(dohURL)
	if err != nil {
		return "", fmt.Errorf("无效的 DoH URL: %v", err)
	}

	dnsQuery := buildDNSQuery(domain, typeHTTPS)
	dnsBase64 := base64.RawURLEncoding.EncodeToString(dnsQuery)

	q := u.Query()
	q.Set("dns", dnsBase64)
	u.RawQuery = q.Encode()

	req, err := http.NewRequest("GET", u.String(), nil)
	if err != nil {
		return "", fmt.Errorf("创建请求失败: %v", err)
	}
	req.Header.Set("Accept", "application/dns-message")
	req.Header.Set("Content-Type", "application/dns-message")

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("DoH 请求失败: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("DoH 服务器返回错误: %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("读取 DoH 响应失败: %v", err)
	}

	return parseDNSResponse(body)
}

func buildDNSQuery(domain string, qtype uint16) []byte {
	query := make([]byte, 0, 512)
	query = append(query, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)
	for _, label := range strings.Split(domain, ".") {
		query = append(query, byte(len(label)))
		query = append(query, []byte(label)...)
	}
	query = append(query, 0x00, byte(qtype>>8), byte(qtype), 0x00, 0x01)
	return query
}

func parseDNSResponse(response []byte) (string, error) {
	if len(response) < 12 {
		return "", errors.New("响应过短")
	}
	ancount := binary.BigEndian.Uint16(response[6:8])
	if ancount == 0 {
		return "", errors.New("无应答记录")
	}

	offset := 12
	for offset < len(response) && response[offset] != 0 {
		offset += int(response[offset]) + 1
	}
	offset += 5

	for i := 0; i < int(ancount); i++ {
		if offset >= len(response) {
			break
		}
		if response[offset]&0xC0 == 0xC0 {
			offset += 2
		} else {
			for offset < len(response) && response[offset] != 0 {
				offset += int(response[offset]) + 1
			}
			offset++
		}
		if offset+10 > len(response) {
			break
		}
		rrType := binary.BigEndian.Uint16(response[offset : offset+2])
		offset += 8
		dataLen := binary.BigEndian.Uint16(response[offset : offset+2])
		offset += 2
		if offset+int(dataLen) > len(response) {
			break
		}
		data := response[offset : offset+int(dataLen)]
		offset += int(dataLen)

		if rrType == typeHTTPS {
			if ech := parseHTTPSRecord(data); ech != "" {
				return ech, nil
			}
		}
	}
	return "", nil
}

func parseHTTPSRecord(data []byte) string {
	if len(data) < 2 {
		return ""
	}
	offset := 2
	if offset < len(data) && data[offset] == 0 {
		offset++
	} else {
		for offset < len(data) && data[offset] != 0 {
			offset += int(data[offset]) + 1
		}
		offset++
	}
	for offset+4 <= len(data) {
		key := binary.BigEndian.Uint16(data[offset : offset+2])
		length := binary.BigEndian.Uint16(data[offset+2 : offset+4])
		offset += 4
		if offset+int(length) > len(data) {
			break
		}
		value := data[offset : offset+int(length)]
		offset += int(length)
		if key == 5 {
			return base64.StdEncoding.EncodeToString(value)
		}
	}
	return ""
}

// ======================== WebSocket 连接 ========================

func (c *ECHClient) parseServerAddr() (host, port, path string, err error) {
	addr := c.serverAddr
	path = "/"
	slashIdx := strings.Index(addr, "/")
	if slashIdx != -1 {
		path = addr[slashIdx:]
		addr = addr[:slashIdx]
	}

	host, port, err = net.SplitHostPort(addr)
	if err != nil {
		return "", "", "", fmt.Errorf("无效的服务器地址格式: %v", err)
	}

	return host, port, path, nil
}

func (c *ECHClient) dialWebSocketWithECH() (*websocket.Conn, error) {
	host, port, path, err := c.parseServerAddr()
	if err != nil {
		return nil, err
	}

	wsURL := fmt.Sprintf("wss://%s:%s%s", host, port, path)

	echBytes, echErr := c.getECHList()
	if echErr != nil {
		return nil, echErr
	}

	tlsCfg, tlsErr := c.buildTLSConfigWithECH(host, echBytes)
	if tlsErr != nil {
		return nil, tlsErr
	}

	dialer := websocket.Dialer{
		TLSClientConfig: tlsCfg,
		Subprotocols: func() []string {
			if c.token == "" {
				return nil
			}
			return []string{c.token}
		}(),
		HandshakeTimeout: 10 * time.Second,
	}

	if c.serverIP != "" {
		dialer.NetDial = func(network, address string) (net.Conn, error) {
			_, port, err := net.SplitHostPort(address)
			if err != nil {
				return nil, err
			}
			return net.DialTimeout(network, net.JoinHostPort(c.serverIP, port), 10*time.Second)
		}
	}

	wsConn, _, dialErr := dialer.Dial(wsURL, nil)
	if dialErr != nil {
		return nil, dialErr
	}

	return wsConn, nil
}

// ======================== SOCKS5 处理 ========================

func (c *ECHClient) handleSOCKS5(conn net.Conn, firstByte byte) {
	if firstByte != 0x05 {
		return
	}

	buf := make([]byte, 1)
	if _, err := io.ReadFull(conn, buf); err != nil {
		return
	}

	nmethods := buf[0]
	methods := make([]byte, nmethods)
	if _, err := io.ReadFull(conn, methods); err != nil {
		return
	}

	if _, err := conn.Write([]byte{0x05, 0x00}); err != nil {
		return
	}

	buf = make([]byte, 4)
	if _, err := io.ReadFull(conn, buf); err != nil {
		return
	}

	if buf[0] != 5 || buf[1] != 0x01 {
		return
	}

	atyp := buf[3]

	var host string
	switch atyp {
	case 0x01:
		buf = make([]byte, 4)
		if _, err := io.ReadFull(conn, buf); err != nil {
			return
		}
		host = net.IP(buf).String()

	case 0x03:
		buf = make([]byte, 1)
		if _, err := io.ReadFull(conn, buf); err != nil {
			return
		}
		domainBuf := make([]byte, buf[0])
		if _, err := io.ReadFull(conn, domainBuf); err != nil {
			return
		}
		host = string(domainBuf)

	case 0x04:
		buf = make([]byte, 16)
		if _, err := io.ReadFull(conn, buf); err != nil {
			return
		}
		host = net.IP(buf).String()

	default:
		conn.Write([]byte{0x05, 0x08, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00})
		return
	}

	buf = make([]byte, 2)
	if _, err := io.ReadFull(conn, buf); err != nil {
		return
	}
	port := int(buf[0])<<8 | int(buf[1])

	var target string
	if atyp == 0x04 {
		target = fmt.Sprintf("[%s]:%d", host, port)
	} else {
		target = fmt.Sprintf("%s:%d", host, port)
	}

	c.log("[SOCKS5] -> %s", target)

	if err := c.handleTunnel(conn, target); err != nil {
		c.log("[SOCKS5] 代理失败: %v", err)
	}
}

func (c *ECHClient) handleTunnel(clientConn net.Conn, target string) error {
	wsConn, err := c.dialWebSocketWithECH()
	if err != nil {
		clientConn.Write([]byte{0x05, 0x04, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00})
		return fmt.Errorf("WebSocket 连接失败: %w", err)
	}
	defer wsConn.Close()

	// 发送目标地址
	if err := wsConn.WriteMessage(websocket.TextMessage, []byte(target)); err != nil {
		clientConn.Write([]byte{0x05, 0x04, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00})
		return fmt.Errorf("发送目标地址失败: %w", err)
	}

	// 发送 SOCKS5 成功响应
	clientConn.Write([]byte{0x05, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00})

	// 双向转发
	var wg sync.WaitGroup
	wg.Add(2)

	// 客户端 -> WebSocket
	go func() {
		defer wg.Done()
		buf := make([]byte, 32*1024)
		for {
			n, err := clientConn.Read(buf)
			if err != nil {
				return
			}
			if err := wsConn.WriteMessage(websocket.BinaryMessage, buf[:n]); err != nil {
				return
			}
		}
	}()

	// WebSocket -> 客户端
	go func() {
		defer wg.Done()
		for {
			_, data, err := wsConn.ReadMessage()
			if err != nil {
				return
			}
			if _, err := clientConn.Write(data); err != nil {
				return
			}
		}
	}()

	wg.Wait()
	return nil
}

// ======================== DoH 代理 ========================

func (c *ECHClient) queryDoHForProxy(dnsQuery []byte) ([]byte, error) {
	_, port, _, err := c.parseServerAddr()
	if err != nil {
		return nil, err
	}

	dohURL := fmt.Sprintf("https://cloudflare-dns.com:%s/dns-query", port)

	echBytes, err := c.getECHList()
	if err != nil {
		return nil, fmt.Errorf("获取 ECH 配置失败: %w", err)
	}

	tlsCfg, err := c.buildTLSConfigWithECH("cloudflare-dns.com", echBytes)
	if err != nil {
		return nil, fmt.Errorf("构建 TLS 配置失败: %w", err)
	}

	transport := &http.Transport{
		TLSClientConfig: tlsCfg,
	}

	if c.serverIP != "" {
		transport.DialContext = func(ctx context.Context, network, addr string) (net.Conn, error) {
			_, port, err := net.SplitHostPort(addr)
			if err != nil {
				return nil, err
			}
			dialer := &net.Dialer{
				Timeout: 10 * time.Second,
			}
			return dialer.DialContext(ctx, network, net.JoinHostPort(c.serverIP, port))
		}
	}

	client := &http.Client{
		Transport: transport,
		Timeout:   10 * time.Second,
	}

	req, err := http.NewRequest("POST", dohURL, bytes.NewReader(dnsQuery))
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", "application/dns-message")
	req.Header.Set("Accept", "application/dns-message")

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("DoH 请求失败: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("DoH 响应错误: %d", resp.StatusCode)
	}

	return io.ReadAll(resp.Body)
}
