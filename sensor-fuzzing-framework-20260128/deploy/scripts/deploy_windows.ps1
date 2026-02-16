$ErrorActionPreference = "Stop"

Set-StrictMode -Version Latest

function Test-CommandExists {
	param([Parameter(Mandatory = $true)][string]$CommandName)
	return [bool](Get-Command $CommandName -ErrorAction SilentlyContinue)
}

function Invoke-CheckedCommand {
	param(
		[Parameter(Mandatory = $true)][string]$Command,
		[Parameter(Mandatory = $true)][string[]]$Arguments,
		[Parameter(Mandatory = $true)][string]$StepName,
		[string]$FailureHint
	)

	Write-Host $StepName -ForegroundColor Cyan
	& $Command @Arguments
	if ($LASTEXITCODE -ne 0) {
		if ($FailureHint) {
			Write-Host $FailureHint -ForegroundColor Yellow
		}
		throw "Step failed: $StepName"
	}
}

function Invoke-DockerPullWithRetry {
	param(
		[string]$Image = "python:3.11-slim",
		[int]$Retries = 3,
		[int]$DelaySeconds = 5
	)

	for ($attempt = 1; $attempt -le $Retries; $attempt++) {
		Write-Host "Pre-pulling base image ($attempt/$Retries): $Image" -ForegroundColor Cyan
		& docker pull $Image
		if ($LASTEXITCODE -eq 0) {
			return
		}

		if ($attempt -lt $Retries) {
			Write-Host "Pull failed, retrying in $DelaySeconds seconds..." -ForegroundColor Yellow
			Start-Sleep -Seconds $DelaySeconds
		}
	}

	& docker image inspect $Image *> $null
	if ($LASTEXITCODE -eq 0) {
		Write-Host "Pull failed, but local cached image exists. Continue with local image: $Image" -ForegroundColor Yellow
		return
	}

	throw "Cannot pull image $Image and no local cache is available. Check registry/network settings."
}

function Install-BaseDeps {
	param(
		[string]$ProjectRoot = $(Join-Path $PSScriptRoot "..\..")
	)
	Push-Location $ProjectRoot
	python -m venv .venv
	.\.venv\Scripts\python.exe -m pip install --upgrade pip
	.\.venv\Scripts\python.exe -m pip install -r consolidated_requirements.txt
	Pop-Location
}

function Install-OptionalDeps {
	param(
		[string]$ProjectRoot = $(Join-Path $PSScriptRoot "..\.."),
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
		[string]$ProjectRoot = $(Join-Path $PSScriptRoot "..\..")
	)
	Push-Location $ProjectRoot
	docker build -t sensor-fuzz:latest -f deploy/Dockerfile .
	Pop-Location
}

function Start-OneClickDockerFuzz {
	param(
		[string]$ProjectRoot = $(Join-Path $PSScriptRoot "..\.."),
		[string]$ComposeFile = "deploy/docker-compose.yml",
		[string]$BaseImage = "python:3.11-slim",
		[string]$PipIndexUrl = "https://pypi.org/simple",
		[string]$PipTrustedHost = "pypi.org",
		[switch]$SkipTests,
		[switch]$KeepRunning
	)

	if (-not (Test-CommandExists -CommandName "docker")) {
		throw "Docker command not found. Please install Docker Desktop first."
	}

	Push-Location $ProjectRoot
	try {
		$composeArgsBase = @("compose", "-f", $ComposeFile)

		Invoke-CheckedCommand -Command "docker" -Arguments @("info") -StepName "Checking Docker engine status..."
		Invoke-DockerPullWithRetry -Image $BaseImage -Retries 3 -DelaySeconds 6

		Invoke-CheckedCommand -Command "docker" -Arguments ($composeArgsBase + @("build", "--build-arg", "BASE_IMAGE=$BaseImage", "--build-arg", "PIP_INDEX_URL=$PipIndexUrl", "--build-arg", "PIP_TRUSTED_HOST=$PipTrustedHost", "sensor-fuzz")) -StepName "Building Docker image..." -FailureHint "Build failed. You can retry with mirror settings: -BaseImage docker.m.daocloud.io/library/python:3.11-slim -PipIndexUrl https://pypi.tuna.tsinghua.edu.cn/simple -PipTrustedHost pypi.tuna.tsinghua.edu.cn"
		Invoke-CheckedCommand -Command "docker" -Arguments ($composeArgsBase + @("up", "-d", "sensor-fuzz")) -StepName "Starting Docker container..."

		if (-not $SkipTests) {
			Invoke-CheckedCommand -Command "docker" -Arguments ($composeArgsBase + @("exec", "-T", "sensor-fuzz", "python", "-c", "import sensor_fuzz; print('smoke test ok')")) -StepName "Running tests..."
		}

		Write-Host "Start succeeded. Service URL: http://localhost:8000" -ForegroundColor Green
		if (-not $KeepRunning) {
			Invoke-CheckedCommand -Command "docker" -Arguments ($composeArgsBase + @("down")) -StepName "Stopping Docker container..."
		}
	}
	finally {
		Pop-Location
	}
}

Write-Host "Windows deploy helper"
Write-Host "- Call Install-BaseDeps to install core libs"
Write-Host "- Call Install-OptionalDeps -AI -Capture -Report to install optional stacks"
Write-Host "- Call Install-Docker to build image"
Write-Host "- Call Start-OneClickDockerFuzz for one-click build/start/test"
