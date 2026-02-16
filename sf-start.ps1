param(
    # 跳过容器内冒烟测试（仅构建并启动）
    [switch]$SkipTests,
    # 使用国内镜像源加速拉取与安装
    [switch]$UseMirror
)

# 将当前目录切换到项目根目录，确保相对路径可用
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

# 导入部署函数集合
. .\deploy\scripts\deploy_windows.ps1

if ($UseMirror) {
    Start-OneClickDockerFuzz -KeepRunning -SkipTests:$SkipTests -BaseImage docker.m.daocloud.io/library/python:3.11-slim -PipIndexUrl https://pypi.tuna.tsinghua.edu.cn/simple -PipTrustedHost pypi.tuna.tsinghua.edu.cn
}
else {
    Start-OneClickDockerFuzz -KeepRunning -SkipTests:$SkipTests
}
