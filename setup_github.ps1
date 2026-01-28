# GitHub仓库快速设置脚本 (PowerShell)
# 使用前请先创建GitHub仓库并获取URL

param(
    [Parameter(Mandatory=$true)]
    [string]$GitHubUrl,

    [Parameter(Mandatory=$false)]
    [string]$BranchName = "main"
)

Write-Host "🚀 GitHub仓库连接设置" -ForegroundColor Green
Write-Host "============================" -ForegroundColor Green

# 检查Git状态
Write-Host "📋 检查Git状态..." -ForegroundColor Yellow
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "⚠️ 工作区有未提交的更改，请先提交或暂存" -ForegroundColor Yellow
    Write-Host $gitStatus
    exit 1
}

# 添加远程仓库
Write-Host "🔗 添加远程仓库..." -ForegroundColor Yellow
try {
    git remote add origin $GitHubUrl
    Write-Host "✅ 远程仓库已添加" -ForegroundColor Green
} catch {
    Write-Host "ℹ️ 远程仓库已存在，更新URL..." -ForegroundColor Yellow
    git remote set-url origin $GitHubUrl
}

# 重命名分支（如果需要）
$currentBranch = git branch --show-current
if ($currentBranch -ne $BranchName) {
    Write-Host "🔄 重命名分支为 $BranchName..." -ForegroundColor Yellow
    git branch -M $BranchName
}

# 推送代码
Write-Host "📤 推送代码到GitHub..." -ForegroundColor Yellow
try {
    git push -u origin $BranchName
    Write-Host "✅ 代码推送成功!" -ForegroundColor Green
} catch {
    Write-Host "❌ 推送失败: $_" -ForegroundColor Red
    Write-Host "请检查："
    Write-Host "1. GitHub URL是否正确"
    Write-Host "2. 是否有推送权限"
    Write-Host "3. 网络连接是否正常"
    exit 1
}

# 创建初始标签
Write-Host "🏷️ 创建初始标签..." -ForegroundColor Yellow
git tag v0.1.0
git push origin v0.1.0

Write-Host "" -ForegroundColor White
Write-Host "🎉 GitHub仓库设置完成!" -ForegroundColor Green
Write-Host "" -ForegroundColor White
Write-Host "📋 后续步骤：" -ForegroundColor Cyan
Write-Host "1. 访问: $GitHubUrl" -ForegroundColor White
Write-Host "2. 在仓库设置中启用GitHub Pages" -ForegroundColor White
Write-Host "3. 添加仓库描述和话题标签" -ForegroundColor White
Write-Host "4. 启用Issues和Discussions" -ForegroundColor White
Write-Host "5. 查看 docs/GITHUB_SETUP.md 获取详细配置指南" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "🔗 重要链接：" -ForegroundColor Yellow
Write-Host "仓库地址: $GitHubUrl" -ForegroundColor White
Write-Host "发布页面: $($GitHubUrl -replace '\.git$', '/releases')" -ForegroundColor White
Write-Host "问题跟踪: $($GitHubUrl -replace '\.git$', '/issues')" -ForegroundColor White</content>
<parameter name="filePath">C:\Users\31601\Desktop\学年论文2\setup_github.ps1