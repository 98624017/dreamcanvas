param(
    [string]$Project = "apps/desktop",
    [switch]$InstallBrowsers
)

Write-Host "[DreamCanvas] 启动 Playwright E2E" -ForegroundColor Cyan

$projectPath = Resolve-Path (Join-Path $PSScriptRoot "..\$Project")
Push-Location $projectPath

try {
    if ($InstallBrowsers) {
        pnpm exec playwright install --with-deps
    }
    pnpm exec playwright test
}
finally {
    Pop-Location
}
