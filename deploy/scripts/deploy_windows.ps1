$ErrorActionPreference = "Stop"

Set-StrictMode -Version Latest

# 说明：本脚本用于 Windows 场景下一键构建并启动 Docker 化测试服务。
# 设计原则：步骤可复用、失败可中断、错误信息可定位。

function Test-CommandExists {
	# 功能：检查命令是否存在（如 docker、python）。
	param([Parameter(Mandatory = $true)][string]$CommandName)
	return [bool](Get-Command $CommandName -ErrorAction SilentlyContinue)
}

function Invoke-CheckedCommand {
	# 功能：统一执行外部命令，并在失败时抛出异常。
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
	# 功能：拉取基础镜像并自动重试，降低网络抖动导致的失败率。
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
	# 功能：创建虚拟环境并安装核心依赖。
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
	# 功能：按需安装可选组件（AI/抓包/报告）。
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
	# 功能：构建本地 Docker 镜像。
	param(
		[string]$ProjectRoot = $(Join-Path $PSScriptRoot "..\..")
	)
	Push-Location $ProjectRoot
	docker build -t sensor-fuzz:latest -f deploy/Dockerfile .
	Pop-Location
}

function Start-OneClickDockerFuzz {
	# 功能：执行一键流程（引擎检查 -> 拉镜像 -> 构建 -> 启动 -> 冒烟测试）。
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

		Write-Host "Start succeeded." -ForegroundColor Green
		Write-Host "Dashboard URL: http://localhost:8080" -ForegroundColor Green
		Write-Host "Metrics URL: http://localhost:8000/metrics" -ForegroundColor Green
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
