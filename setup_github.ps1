#requires -Version 5.1
# GitHub repository config script (PowerShell)
# Generates github_config.ini for SIL-compliance sensor fuzzing framework
# Version: 1.2 (Fully fixed)
# Author: Industrial sensor fuzzing framework team

# 核心修复：param块放在脚本最顶部，确保参数绑定
param(
    [Parameter(Mandatory=$true, HelpMessage="GitHub repository URL, with or without .git suffix")]
    [ValidateNotNullOrEmpty()]
    [string]$GitHubUrl
)

# Force UTF-8 output to avoid mojibake (removed non-ASCII)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Set-StrictMode -Version Latest

# 最佳实践：函数命名符合Verb-Noun规范
function Normalize-RepositoryUrl {
    param([string]$Url)
    $trimmed = $Url.Trim()
    if (-not ($trimmed -match '^https?://')) {
        throw "URL must start with http:// or https://"
    }
    # Remove trailing .git then any trailing slash
    $noGit = $trimmed -replace '\.git$', ''
    return $noGit.TrimEnd('/')
}

function Main {
    Write-Host "GitHub repository configuration" -ForegroundColor Green
    Write-Host "================================" -ForegroundColor Green

    try {
        # 核心修复：显式传参，避免跨作用域引用
        $cleanUrl = Normalize-RepositoryUrl -Url $GitHubUrl
        Write-Host "Normalized URL: $cleanUrl" -ForegroundColor Yellow

        $issuesUrl = "$cleanUrl/issues"
        Write-Host "Issues URL: $issuesUrl" -ForegroundColor Yellow

        Write-Host "Writing config file..." -ForegroundColor Yellow
        $configContent = @"
[GitHub]
RepositoryUrl=$cleanUrl
IssuesUrl=$issuesUrl
ConfiguredAt=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Framework=Industrial sensor fuzzing framework
Compliance=SIL compliance validation
"@

        # 最佳实践：使用Join-Path拼接路径，指定UTF-8编码
        $configPath = Join-Path -Path $PSScriptRoot -ChildPath "github_config.ini"
        $configContent | Out-File -FilePath $configPath -Encoding UTF8 -Force -ErrorAction Stop
        Write-Host "Config file written: github_config.ini" -ForegroundColor Green

    } catch {
        # 完善异常处理：清晰错误提示
        Write-Host "Configuration failed: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Check URL format and file write permissions." -ForegroundColor Red
        exit 1
    } finally {
        # 完善异常处理：finally块收尾
        Write-Host "Configuration process completed." -ForegroundColor Cyan
    }

    Write-Host "" -ForegroundColor White
    Write-Host "Summary:" -ForegroundColor Cyan
    Write-Host "Repository URL: $cleanUrl" -ForegroundColor White
    Write-Host "Issues URL: $issuesUrl" -ForegroundColor White
    Write-Host "Config file: github_config.ini" -ForegroundColor White
}

Main