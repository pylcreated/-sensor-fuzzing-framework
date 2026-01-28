$ErrorActionPreference = "Stop"

function Install-BaseDeps {
	param(
		[string]$ProjectRoot = "$PSScriptRoot/../.."
	)
	Push-Location $ProjectRoot
	python -m venv .venv
	.\.venv\Scripts\python.exe -m pip install --upgrade pip
	.\.venv\Scripts\python.exe -m pip install -r requirements.txt
	Pop-Location
}

function Install-OptionalDeps {
	param(
		[string]$ProjectRoot = "$PSScriptRoot/../..",
		[switch]$AI,
		[switch]$Capture,
		[switch]$Report
	)
	Push-Location $ProjectRoot
	if ($AI) { .\.venv\Scripts\python.exe -m pip install -r requirements-optional-ai.txt }
	if ($Capture) { .\.venv\Scripts\python.exe -m pip install -r requirements-optional-capture.txt }
	if ($Report) { .\.venv\Scripts\python.exe -m pip install -r requirements-optional-report.txt }
	Pop-Location
}

function Install-Docker {
	param(
		[string]$ProjectRoot = "$PSScriptRoot/../.."
	)
	Push-Location $ProjectRoot
	docker build -t sensor-fuzz:latest -f deploy/Dockerfile .
	Pop-Location
}

Write-Host "Windows deploy helper"
Write-Host "- Call Install-BaseDeps to install core libs"
Write-Host "- Call Install-OptionalDeps -AI -Capture -Report to install optional stacks"
Write-Host "- Call Install-Docker to build image"
