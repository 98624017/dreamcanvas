param(
    [Parameter(Mandatory)]
    [string]$InputPath,
    [string]$OutputPath = "redacted.log"
)

if (-not (Test-Path $InputPath)) {
    throw "找不到输入文件：$InputPath"
}

(Get-Content $InputPath -Raw) -replace '(sessionid=)([A-Za-z0-9]+)', '$1****' |
    Set-Content -Encoding UTF8 $OutputPath

Write-Host "已输出脱敏日志：$OutputPath" -ForegroundColor Green
