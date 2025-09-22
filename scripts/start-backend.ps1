param(
    [switch]$Reload,
    [int]$Port = 18500,
    [string]$ListenHost = "127.0.0.1",
    [switch]$Detached
)

Write-Host "[DreamCanvas] 启动 FastAPI 后端" -ForegroundColor Cyan

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$apiPath = Join-Path $root "src-py"

Push-Location $apiPath

try {
    $arguments = @(
        "-m",
        "poetry",
        "run",
        "uvicorn",
        "dreamcanvas.app:app",
        "--host",
        $ListenHost,
        "--port",
        $Port
    )

    if ($Reload) {
        $arguments += "--reload"
    }

    Write-Host "执行命令：python $($arguments -join ' ')" -ForegroundColor Gray

    if ($Detached) {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "python"
        $psi.Arguments = $arguments -join ' '
        $psi.WorkingDirectory = $apiPath
        $psi.CreateNoWindow = $true
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true

        $process = [System.Diagnostics.Process]::Start($psi)
        Write-Host "后端已在后台启动，PID：$($process.Id)" -ForegroundColor Green
    }
    else {
        $process = Start-Process -FilePath "python" -ArgumentList $arguments -PassThru
        Write-Host "后端进程 PID：$($process.Id)" -ForegroundColor Green
        $process.WaitForExit()
    }
}
finally {
    Pop-Location
}
