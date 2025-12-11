# 触发 GitHub Actions 工作流来创建 Release
# 这个脚本会创建一个空提交来触发工作流

$ErrorActionPreference = "Stop"

Write-Host "🚀 准备触发 GitHub Actions 工作流..."
Write-Host ""

# 检查当前分支
$currentBranch = git branch --show-current
Write-Host "当前分支: $currentBranch"

if ($currentBranch -ne "main") {
    Write-Host "⚠️  警告: 当前不在 main 分支"
    Write-Host "是否切换到 main 分支? (y/N): " -NoNewline
    $response = Read-Host
    if ($response -eq "y") {
        git checkout main
    }
    else {
        Write-Host "❌ 取消操作"
        exit 0
    }
}

# 拉取最新代码
Write-Host "📥 拉取最新代码..."
git pull origin main

# 创建一个空提交来触发工作流
Write-Host "📝 创建触发提交..."
git commit --allow-empty -m "触发: 重新创建 Release (无需重新构建)"

# 推送到远程
Write-Host "📤 推送到 GitHub..."
git push origin main

Write-Host ""
Write-Host "✅ 已触发 GitHub Actions 工作流!"
Write-Host "📋 查看构建状态:"
Write-Host "   https://github.com/zhengwuji/ech-ipa/actions"
Write-Host ""
Write-Host "⏱️  等待几分钟后，Release 将自动创建"
Write-Host "📦 Release 页面:"
Write-Host "   https://github.com/zhengwuji/ech-ipa/releases"
