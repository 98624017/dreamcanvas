param(
    [switch]$IncludeE2E,
    [switch]$InstallBrowsers,
    [string]$OutputPath = "self-test-report.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $root

$results = @()
$overallSuccess = $true

function Invoke-Step {
    param([
        Parameter(Mandatory)]
        [string]$Name,
        [Parameter(Mandatory)]
        [ScriptBlock]$Action
    )

    $stepResult = [ordered]@{
        name   = $Name
        status = "success"
        startedAt = (Get-Date).ToString("o")
        durationMs = 0
        error = $null
    }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        Set-Variable -Name LASTEXITCODE -Value 0 -Scope global
        & $Action
        if ($LASTEXITCODE -ne 0) {
            throw "命令返回非零退出码：$LASTEXITCODE"
        }
    }
    catch {
        $stepResult.status = "failure"
        $stepResult.error = $_.Exception.Message
        $script:overallSuccess = $false
    }
    finally {
        $sw.Stop()
        $stepResult.durationMs = [math]::Round($sw.Elapsed.TotalMilliseconds, 0)
        $script:results += [pscustomobject]$stepResult
    }
}

Invoke-Step -Name "pnpm lint" -Action {
    pnpm --filter @dreamcanvas/desktop lint | Write-Host
}

Invoke-Step -Name "markdownlint" -Action {
    pnpm run lint:docs | Write-Host
}

Invoke-Step -Name "pnpm test" -Action {
    pnpm --filter @dreamcanvas/desktop test | Write-Host
}

Invoke-Step -Name "poetry pytest" -Action {
    Push-Location (Join-Path $root "src-py")
    try {
        python -m poetry run pytest | Write-Host
    }
    finally {
        Pop-Location
    }
}

if ($IncludeE2E) {
    Invoke-Step -Name "playwright e2e" -Action {
        $params = @{}
        if ($InstallBrowsers) {
            $params.InstallBrowsers = $true
        }
        & (Join-Path $root "scripts/run-e2e.ps1") @params | Write-Host
    }
}

$report = [ordered]@{
    generatedAt = (Get-Date).ToString("o")
    root = $root.Path
    includeE2E = [bool]$IncludeE2E
    steps = $results
    success = $overallSuccess
}

$report | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $OutputPath

Pop-Location

if (-not $overallSuccess) {
    Write-Error "Self-test failed. See $OutputPath for details." -ErrorAction Stop
}
else {
    Write-Host "Self-test completed successfully. Report saved to $OutputPath" -ForegroundColor Green
}
