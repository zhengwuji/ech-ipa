-- ECH Workers Proxy LuCI Configuration
-- 完整功能界面，匹配 Windows 版本

local sys = require "luci.sys"
local uci = require "luci.model.uci".cursor()

m = Map("ech-wk", translate("ECH Workers Proxy"), translate("ECH Workers 代理客户端配置"))

-- ========== 服务状态与控制 ==========
s = m:section(TypedSection, "ech-wk", translate("服务控制"))
s.anonymous = true
s.addremove = false

-- 运行状态显示
local running = (sys.call("pidof ech-wk > /dev/null") == 0)
local status_text = running and 
    '<span style="color:green;font-weight:bold;">● 运行中</span>' or 
    '<span style="color:red;font-weight:bold;">○ 已停止</span>'

o = s:option(DummyValue, "_status", translate("运行状态"))
o.rawhtml = true
o.cfgvalue = function(self, section)
    return status_text
end

-- 启用开关
o = s:option(Flag, "enabled", translate("启用服务"))
o.rmempty = false

-- 开机自启
o = s:option(Flag, "auto_start", translate("开机自启"))
o.default = "1"
o.rmempty = false

-- ========== 服务器管理 ==========
server = m:section(TypedSection, "server", translate("服务器管理"),
    translate("可添加多个服务器配置，选择一个作为当前使用的服务器"))
server.template = "cbi/tblsection"
server.anonymous = true
server.addremove = true
server.sortable = true

o = server:option(Value, "name", translate("服务器名称"))
o.rmempty = false
o.placeholder = "默认服务器"

o = server:option(Value, "server_addr", translate("服务地址"))
o.rmempty = false
o.placeholder = "x.workers.dev:443"

o = server:option(Value, "token", translate("身份令牌"))
o.password = true
o.rmempty = true

o = server:option(Flag, "active", translate("当前使用"))
o.rmempty = false

-- ========== 核心配置 ==========
core = m:section(NamedSection, "general", "ech-wk", translate("核心配置"))
core.anonymous = true
core.addremove = false

o = core:option(Value, "listen_addr", translate("监听地址"))
o.default = "127.0.0.1:30000"
o.placeholder = "127.0.0.1:30000"

-- ========== 高级选项 ==========
adv = m:section(NamedSection, "general", "ech-wk", translate("高级选项（可选）"))
adv.anonymous = true
adv.addremove = false

o = adv:option(Value, "server_ip", translate("优选IP/域名"),
    translate("指定服务器IP以绕过DNS解析"))
o.rmempty = true
o.placeholder = "例如: saas.sin.fan"

o = adv:option(Value, "dns_server", translate("DOH服务器"))
o.default = "dns.alidns.com/dns-query"
o.placeholder = "dns.alidns.com/dns-query"

o = adv:option(Value, "ech_domain", translate("ECH域名"))
o.default = "cloudflare-ech.com"
o.placeholder = "cloudflare-ech.com"

-- ========== 分流设置 ==========
routing = m:section(NamedSection, "general", "ech-wk", translate("分流设置"))
routing.anonymous = true
routing.addremove = false

o = routing:option(ListValue, "proxy_mode", translate("代理模式"))
o:value("global", translate("全局代理"))
o:value("bypass_cn", translate("跳过中国大陆"))
o:value("gfwlist", translate("仅代理被墙站点"))
o:value("direct", translate("直连（不代理）"))
o.default = "bypass_cn"

-- ========== 运行日志 ==========
log = m:section(TypedSection, "ech-wk", translate("运行日志"))
log.anonymous = true
log.addremove = false

o = log:option(TextValue, "_log")
o.rows = 15
o.readonly = true
o.cfgvalue = function(self, section)
    local log_content = sys.exec("tail -n 50 /tmp/ech-wk.log 2>/dev/null || echo '暂无日志'")
    return log_content
end

o = log:option(Button, "_clear_log", translate("清空日志"))
o.inputstyle = "remove"
o.write = function(self, section)
    sys.exec("echo '' > /tmp/ech-wk.log")
end

return m
