param(
    [string]$OutputPath = "dreamcanvas-diagnostics.zip",
    [switch]$IncludeSelfTest,
    [switch]$IncludePoetryTree
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$workspace = Join-Path ([System.IO.Path]::GetTempPath()) ("dreamcanvas-diag-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $workspace | Out-Null

try {
    $metadataDir = Join-Path $workspace "metadata"
    New-Item -ItemType Directory -Path $metadataDir | Out-Null

    # 基本信息
    (Get-Date).ToString("o") | Set-Content -Encoding UTF8 (Join-Path $metadataDir "timestamp.txt")
    pnpm --version | Set-Content -Encoding UTF8 (Join-Path $metadataDir "pnpm-version.txt")
    node --version | Set-Content -Encoding UTF8 (Join-Path $metadataDir "node-version.txt")
    python --version | Set-Content -Encoding UTF8 (Join-Path $metadataDir "python-version.txt")
    try { python -m poetry --version } catch { $_.Exception.Message } | Set-Content -Encoding UTF8 (Join-Path $metadataDir "poetry-version.txt")

    # 复制运行手册、配置样板
    Copy-Item -Path (Join-Path $root "docs/runbook.md") -Destination $workspace
    Copy-Item -Path (Join-Path $root "config/default.env") -Destination $workspace -ErrorAction SilentlyContinue

    # 收集日志目录
    $logSource = Join-Path $env:LOCALAPPDATA "DreamCanvas\\logs"
    if (Test-Path $logSource) {
        Copy-Item -Path $logSource -Destination (Join-Path $workspace "logs") -Recurse -ErrorAction SilentlyContinue
    }

    if ($IncludeSelfTest) {
        $reportPath = Join-Path $workspace "self-test-report.json"
        & (Join-Path $root "scripts/self-test.ps1") -OutputPath $reportPath | Write-Host
    }

    if ($IncludePoetryTree -and (Get-Command python -ErrorAction SilentlyContinue)) {
        $poetryTreePath = Join-Path $metadataDir "poetry-tree.txt"
        try {
            Push-Location (Join-Path $root "src-py")
            python -m poetry show --tree | Set-Content -Encoding UTF8 $poetryTreePath
        }
        catch {
            $_.Exception.Message | Set-Content -Encoding UTF8 $poetryTreePath
        }
        finally {
            Pop-Location
        }
    }

    if (Test-Path $OutputPath) {
        Remove-Item $OutputPath -Force
    }
    Compress-Archive -Path (Join-Path $workspace '*') -DestinationPath $OutputPath
    Write-Host "诊断包已生成：$OutputPath" -ForegroundColor Green
}
finally {
    Remove-Item $workspace -Recurse -Force -ErrorAction SilentlyContinue
}
