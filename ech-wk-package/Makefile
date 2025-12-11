include $(TOPDIR)/rules.mk

PKG_NAME:=ech-wk
PKG_VERSION:=1.0.0
PKG_RELEASE:=1

PKG_MAINTAINER:=User <user@example.com>
PKG_LICENSE:=MIT

# Go package configuration
PKG_BUILD_DEPENDS:=golang/host
PKG_BUILD_PARALLEL:=1
PKG_USE_MIPS16:=0

GO_PKG:=github.com/user/ech-wk
GO_PKG_LDFLAGS_X:=main.Version=$(PKG_VERSION)
GO_PKG_LDFLAGS:=-s -w
GO_MIPS:=softfloat
GO_MIPS64:=softfloat
GO_PKG_CGO_ENABLED:=0

include $(INCLUDE_DIR)/package.mk
include $(INCLUDE_DIR)/nls.mk
-include $(TOPDIR)/feeds/packages/lang/golang/golang-package.mk

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) ./src/* $(PKG_BUILD_DIR)/
endef

define Package/ech-wk
  SECTION:=net
  CATEGORY:=Network
  TITLE:=ECH Workers Proxy with LuCI
  DEPENDS:=$(GO_ARCH_DEPENDS) +ca-bundle +luci-base
endef

define Package/ech-wk/description
  ECH Workers Proxy Client with integrated LuCI interface.
  一站式安装：包含主程序和 LuCI 管理界面。
endef

define Package/ech-wk/conffiles
/etc/config/ech-wk
endef

# If golang-package.mk is not included, we need manual build instructions
ifndef GO_PKG_BUILD_BIN_DIR
  define Build/Compile
	cd $(PKG_BUILD_DIR)/src && \
	go build -o $(PKG_BUILD_DIR)/ech-wk .
  endef
endif

define Package/ech-wk/install
	# 安装主程序
	$(INSTALL_DIR) $(1)/usr/bin
	$(if $(GO_PKG_BUILD_BIN_DIR),\
		$(INSTALL_BIN) $(GO_PKG_BUILD_BIN_DIR)/ech-wk $(1)/usr/bin/,\
		$(INSTALL_BIN) $(PKG_BUILD_DIR)/ech-wk $(1)/usr/bin/)
	
	# 安装配置文件
	$(INSTALL_DIR) $(1)/etc/config
	$(INSTALL_CONF) ./files/etc/config/ech-wk $(1)/etc/config/ech-wk
	
	# 安装启动脚本
	$(INSTALL_DIR) $(1)/etc/init.d
	$(INSTALL_BIN) ./files/etc/init.d/ech-wk $(1)/etc/init.d/ech-wk
	
	# 安装 LuCI 界面文件
	$(INSTALL_DIR) $(1)/usr/lib/lua/luci/controller
	$(INSTALL_DIR) $(1)/usr/lib/lua/luci/model/cbi
	$(INSTALL_DATA) ./luasrc/controller/ech-wk.lua $(1)/usr/lib/lua/luci/controller/
	$(INSTALL_DATA) ./luasrc/model/cbi/ech-wk.lua $(1)/usr/lib/lua/luci/model/cbi/
	
	# 安装 ACL 权限文件
	$(INSTALL_DIR) $(1)/usr/share/rpcd/acl.d
	$(INSTALL_DATA) ./root/usr/share/rpcd/acl.d/luci-app-ech-wk.json $(1)/usr/share/rpcd/acl.d/
endef

$(eval $(call BuildPackage,ech-wk))
