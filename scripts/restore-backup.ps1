param(
    [Parameter(Mandatory)]
    [string]$Snapshot
)

$backupsDir = Join-Path $env:APPDATA "DreamCanvas\backups"
$projectsDir = Join-Path $env:APPDATA "DreamCanvas\projects"

$source = Join-Path $backupsDir $Snapshot
if (-not (Test-Path $source)) {
    throw "找不到备份文件：$source"
}

Write-Host "即将恢复备份：$source" -ForegroundColor Yellow
Expand-Archive -Path $source -DestinationPath $projectsDir -Force
Write-Host "备份恢复完成" -ForegroundColor Green
