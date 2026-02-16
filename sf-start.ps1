param(
    [switch]$SkipTests,
    [switch]$UseMirror
)

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

. .\deploy\scripts\deploy_windows.ps1

if ($UseMirror) {
    Start-OneClickDockerFuzz -KeepRunning -SkipTests:$SkipTests -BaseImage docker.m.daocloud.io/library/python:3.11-slim -PipIndexUrl https://pypi.tuna.tsinghua.edu.cn/simple -PipTrustedHost pypi.tuna.tsinghua.edu.cn
}
else {
    Start-OneClickDockerFuzz -KeepRunning -SkipTests:$SkipTests
}
