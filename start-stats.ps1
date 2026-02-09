# Start SteelSeries OLED stats hidden (no autostart). Run with -h for help.

param(
    [Alias('h')][switch]$Help,
    [switch]$Stop
)

$ErrorActionPreference = 'Stop'
$ExeName = "steelseries.exe"

if ($Help) {
    Write-Host @"
SteelSeries OLED Stats Launcher

USAGE
  .\start-stats.ps1        Start stats display (hidden)
  .\start-stats.ps1 -Stop  Stop running stats process

NOTES
  Builds executable automatically if missing.
  Does not require Administrator.
"@
    exit 0
}

$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { $PWD.Path }
$ExePath = Join-Path $ScriptDir "dist\$ExeName"

if ($Stop) {
    $procs = Get-Process -Name "steelseries" -ErrorAction SilentlyContinue
    if ($procs) {
        $procs | Stop-Process -Force
        Write-Host "Stopped steelseries process(es)" -ForegroundColor Green
    } else {
        Write-Host "No steelseries process running" -ForegroundColor Yellow
    }
    exit 0
}

# Build if missing
if (-not (Test-Path $ExePath)) {
    Write-Host "Executable not found, building..." -ForegroundColor Yellow
    $SpecFile = Join-Path $ScriptDir "steelseries.spec"

    if (-not (Test-Path $SpecFile)) {
        Write-Host "Error: steelseries.spec not found" -ForegroundColor Red
        exit 1
    }

    Push-Location $ScriptDir
    try {
        & uv run pyinstaller steelseries.spec
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error: Build failed" -ForegroundColor Red
            exit 1
        }
    } finally {
        Pop-Location
    }
}

Start-Process $ExePath -ArgumentList "stats"
Write-Host "Stats started. Stop with: .\start-stats.ps1 -Stop" -ForegroundColor Green
