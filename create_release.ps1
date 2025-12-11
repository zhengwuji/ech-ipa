# 手动创建 GitHub Release 的脚本
# 这个脚本会帮助你将已构建的 IPA 文件推送到 GitHub Releases

$ErrorActionPreference = "Stop"

# 配置
$REPO = "zhengwuji/ech-ipa"  # 请根据实际情况修改
$TAG = "ios-swift-pure-v2.0.0-20251211-232800"
$COMMIT_HASH = "5fc80be"
$IPA_NAME = "${COMMIT_HASH}-ECHWorkers-Swift-Pure-unsigned.ipa"

# 检查是否已安装 GitHub CLI
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "❌ 错误: 未安装 GitHub CLI (gh)"
    Write-Host "请访问 https://cli.github.com/ 安装 GitHub CLI"
    Write-Host ""
    Write-Host "或者手动创建 Release:"
    Write-Host "1. 访问 https://github.com/$REPO/releases/new"
    Write-Host "2. Tag: $TAG"
    Write-Host "3. 上传从 GitHub Actions Artifacts 下载的 IPA 文件"
    exit 1
}

# 检查是否已登录
$loginStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 未登录 GitHub CLI"
    Write-Host "请运行: gh auth login"
    exit 1
}

Write-Host "📦 准备创建 Release: $TAG"
Write-Host ""

# 生成 changelog
Write-Host "📝 生成 changelog..."
$lastTag = git describe --tags --abbrev=0 "$TAG^" 2>$null
if ($lastTag) {
    $changelog = git log "$lastTag..$TAG" --pretty=format:"- %s" --no-merges
} else {
    $changelog = git log --pretty=format:"- %s" --no-merges | Select-Object -First 20
}

if (-not $changelog) {
    $changelog = "- Swift 纯原生版本首次发布（无 Go 依赖）"
}

# 创建 Release Body
$releaseBody = @"
# ECH Workers - 纯 Swift 原生版本 2.0

**🎉 完全重写 - 无 Go/gomobile 依赖**

## 特性

- ✅ 100% 纯 Swift 代码
- ✅ 使用 iOS 原生 Network.framework
- ✅ ECH 加密支持（iOS 原生实现）
- ✅ WebSocket 隧道
- ✅ SOCKS5 代理
- ✅ 无任何 Framework 依赖
- ✅ 单一可执行文件
- ✅ 完美适配爱思助手签名

## 安装方法

### 爱思助手（推荐）
1. 下载 ``$IPA_NAME``
2. 打开爱思助手
3. 导入 IPA 并签名安装
4. ✅ 应该能成功签名（纯 Swift，无复杂依赖）

### TrollStore
1. 下载 IPA
2. 在 TrollStore 中安装
3. 打开应用即可使用

## 技术说明

- **无 Go 代码**: 完全移除了 gomobile 和所有 Go 依赖
- **原生 ECH**: 使用 iOS 系统的 TLS 1.3 和 ECH 支持
- **纯 Swift**: 所有网络逻辑使用 Network.framework 实现
- **单一二进制**: 无 Framework，无动态库，只有主执行文件

## 更新日志

$changelog

---

**版本**: 2.0.0-Pure-Swift  
**最低 iOS 版本**: 14.0  
**架构**: arm64  
**Commit**: $COMMIT_HASH

## 📥 下载说明

由于 IPA 文件是在 GitHub Actions 中构建的，请：

1. 访问 [Actions 页面](https://github.com/$REPO/actions)
2. 找到对应的构建任务 (Commit: $COMMIT_HASH)
3. 下载 Artifacts 中的 IPA 文件
4. 将 IPA 文件上传到此 Release
"@

Write-Host "创建 Release Notes..."
Write-Host "----------------------------------------"
Write-Host $releaseBody
Write-Host "----------------------------------------"
Write-Host ""

# 检查 Release 是否已存在
$existingRelease = gh release view $TAG --repo $REPO 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "⚠️  Release 已存在: $TAG"
    Write-Host "是否要删除并重新创建? (y/N): " -NoNewline
    $response = Read-Host
    if ($response -ne "y") {
        Write-Host "❌ 取消操作"
        exit 0
    }
    
    Write-Host "删除现有 Release..."
    gh release delete $TAG --repo $REPO --yes
}

# 创建 Release (不上传文件)
Write-Host "🚀 创建 Release..."
$releaseBody | gh release create $TAG `
    --repo $REPO `
    --title "iOS 纯 Swift 版本 $TAG" `
    --notes-file - `
    --draft

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Release 创建成功 (草稿状态)"
    Write-Host ""
    Write-Host "📋 下一步操作:"
    Write-Host "1. 从 GitHub Actions Artifacts 下载 IPA 文件"
    Write-Host "   链接: https://github.com/$REPO/actions"
    Write-Host "2. 上传 IPA 到 Release:"
    Write-Host "   gh release upload $TAG $IPA_NAME --repo $REPO"
    Write-Host "3. 发布 Release:"
    Write-Host "   gh release edit $TAG --repo $REPO --draft=false"
    Write-Host ""
    Write-Host "或访问: https://github.com/$REPO/releases/tag/$TAG"
} else {
    Write-Host "❌ 创建 Release 失败"
    exit 1
}
