param(
    [switch]$Force
)

Write-Host "[DreamCanvas] 开始运行环境自检..." -ForegroundColor Cyan

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$envFile = Join-Path $root ".env"
$secretsFile = Join-Path $root "config\secrets.enc"
$logDir = Join-Path $env:LOCALAPPDATA "DreamCanvas\logs"
$projectsDir = Join-Path $env:APPDATA "DreamCanvas\projects"
$backupsDir = Join-Path $env:APPDATA "DreamCanvas\backups"

function Test-Command {
    param([string]$Name)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "未找到命令：$Name"
    }
    return $cmd.Source
}

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}
try {
    $pnpmPath = Test-Command -Name "pnpm"
    Write-Host "✓ pnpm 已就绪 ($pnpmPath)"
    $rustcPath = Test-Command -Name "rustc"
    Write-Host "✓ rustc 已就绪 ($rustcPath)"
    $cargoPath = Test-Command -Name "cargo"
    Write-Host "✓ cargo 已就绪 ($cargoPath)"
    $poetryPath = Test-Command -Name "poetry"
    Write-Host "✓ poetry 已就绪 ($poetryPath)"
} catch {
    Write-Error $_
    if (-not $Force) {
        throw "关键依赖缺失，可使用 -Force 忽略"
    }
}

Ensure-Directory -Path $logDir
Ensure-Directory -Path $projectsDir
Ensure-Directory -Path $backupsDir

Write-Host "✓ 日志/项目/备份目录已检查" -ForegroundColor Green
if (-not (Test-Path $envFile)) {
    Write-Host "未检测到 .env，复制 config\default.env" -ForegroundColor Yellow
    Copy-Item (Join-Path $root "config\default.env") $envFile -Force
}

if (-not (Test-Path $secretsFile)) {
    "# 运行示例：dc-cli secrets encrypt --input config/secrets.template.json --output config/secrets.enc" |
        Set-Content -Encoding UTF8 $secretsFile
    Write-Host "已创建占位 secrets.enc，请使用 dc-cli 将明文模板加密后覆盖" -ForegroundColor Yellow
}

Write-Host "当前 Python 解释器：" -NoNewline
$pythonPath = if ($env:DC_PYTHON_BIN) { $env:DC_PYTHON_BIN } else { (Get-Command python -ErrorAction SilentlyContinue)?.Source }
if ($null -eq $pythonPath) {
    Write-Warning "未找到 Python，可在运行 Tauri 前设置 DC_PYTHON_BIN"
} else {
    Write-Host $pythonPath -ForegroundColor Green
}

Write-Host "建议执行命令："
Write-Host "  Shell=PowerShell > pnpm install" -ForegroundColor Gray
Write-Host "  Shell=PowerShell > pnpm --filter @dreamcanvas/desktop tauri" -ForegroundColor Gray
Write-Host "  Shell=PowerShell > scripts/start-backend.ps1 -Reload" -ForegroundColor Gray
Write-Host "  Shell=PowerShell > cd src-py; poetry install" -ForegroundColor Gray
Write-Host "环境自检完成" -ForegroundColor Cyan
