#requires -Version 5.1
# GitHub repository config script (PowerShell)
# Generates github_config.ini for SIL-compliance sensor fuzzing framework
# Version: 1.2

param(
    [Parameter(Mandatory=$true, HelpMessage="GitHub repository URL, with or without .git suffix")]
    [ValidateNotNullOrEmpty()]
    [string]$GitHubUrl
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Set-StrictMode -Version Latest

function Convert-RepositoryUrl {
    param([string]$Url)
    $trimmed = $Url.Trim()
    if (-not ($trimmed -match '^https?://')) {
        throw "URL must start with http:// or https://"
    }
    $noGit = $trimmed -replace '\\.git$', ''
    return $noGit.TrimEnd('/')
}

function Main {
    Write-Host "GitHub repository configuration" -ForegroundColor Green
    Write-Host "================================" -ForegroundColor Green

    try {
        $cleanUrl = Convert-RepositoryUrl -Url $GitHubUrl
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

        $configPath = Join-Path -Path $PSScriptRoot -ChildPath "github_config.ini"
        $configContent | Out-File -FilePath $configPath -Encoding UTF8 -Force -ErrorAction Stop
        Write-Host "Config file written: github_config.ini" -ForegroundColor Green

    } catch {
        Write-Host "Configuration failed: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Check URL format and file write permissions." -ForegroundColor Red
        exit 1
    } finally {
        Write-Host "Configuration process completed." -ForegroundColor Cyan
    }

    Write-Host "" -ForegroundColor White
    Write-Host "Summary:" -ForegroundColor Cyan
    Write-Host "Repository URL: $cleanUrl" -ForegroundColor White
    Write-Host "Issues URL: $issuesUrl" -ForegroundColor White
    Write-Host "Config file: github_config.ini" -ForegroundColor White
}

Main
