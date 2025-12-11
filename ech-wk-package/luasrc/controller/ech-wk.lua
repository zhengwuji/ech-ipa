module("luci.controller.ech-wk", package.seeall)

function index()
	if not nixio.fs.access("/etc/config/ech-wk") then
		return
	end

	entry({"admin", "services", "ech-wk"}, cbi("ech-wk"), _("ECH Workers Proxy"), 100).dependent = true
end
