Write-Host "[DreamCanvas] 启动 k6 性能压测脚本" -ForegroundColor Cyan

$k6 = Get-Command k6 -ErrorAction SilentlyContinue
if (-not $k6) {
    throw "未找到 k6，请参考 docs/DreamCanvas - 详细开发文档.md 安装"
}

$script = Join-Path $PSScriptRoot "..\tests\perf\jimeng-smoke.js"
if (-not (Test-Path $script)) {
    throw "缺少性能脚本：$script"
}

& $k6.Source run $script
