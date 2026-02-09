#Requires -Version 5.1
#Requires -Modules ScheduledTasks

# Auto-start SteelSeries OLED stats at login. Run with -h for help.

[CmdletBinding(DefaultParameterSetName = 'Install')]
param(
    [Parameter(ParameterSetName = 'Help')]
    [Alias('h')]
    [switch]$Help,

    [Parameter(ParameterSetName = 'Uninstall')]
    [switch]$Uninstall,

    [Parameter(ParameterSetName = 'Install')]
    [switch]$StartNow,

    [Parameter(ParameterSetName = 'Install')]
    [Parameter(ParameterSetName = 'Uninstall')]
    [ValidateNotNullOrEmpty()]
    [ValidateScript({
        # Must be absolute path: C:\... or \\server\...
        if ($_ -and -not ($_ -match '^[a-zA-Z]:\\|^\\\\')) {
            throw "ExePath must be an absolute path: $_"
        }
        $true
    })]
    [string]$ExePath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

#region Configuration
$TaskName = "SteelSeriesOLED"
$RestartCount = 3
$RestartIntervalMinutes = 1
#endregion

#region Help Handler
if ($Help) {
    Write-Host @"
SteelSeries OLED Auto-Start Setup

USAGE
  .\setup-autostart.ps1              Install (runs at next login)
  .\setup-autostart.ps1 -StartNow    Install and start now
  .\setup-autostart.ps1 -Uninstall   Remove scheduled task

OPTIONS
  -ExePath <path>    Custom exe path (default: dist\steelseries.exe)
  -h, -?             Show this help

NOTES
  Requires Administrator. Task runs the exe directly with auto-restart on crash.
"@
    exit 0
}
#endregion

#region Helper Functions
function Remove-ExistingTask {
    param([string]$Name, [switch]$Silent)

    $task = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
    if ($task) {
        try {
            Stop-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
            Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction Stop
            if (-not $Silent) {
                Write-Host "Removed scheduled task: $Name" -ForegroundColor Green
            }
            return $true
        } catch {
            Write-Warning "Failed to remove task: $_"
            return $false
        }
    }
    return $false
}

function Remove-LegacyLauncher {
    param([string]$Dir)

    $legacyLauncher = Join-Path $Dir "steelseries-launcher.vbs"
    if (Test-Path $legacyLauncher) {
        Remove-Item $legacyLauncher -Force -ErrorAction SilentlyContinue
        Write-Host "Removed legacy VBS launcher" -ForegroundColor Yellow
    }
}
#endregion

#region Resolve Executable Path
if (-not $ExePath) {
    $ScriptDir = if ($PSScriptRoot) { $PSScriptRoot }
                 elseif ($MyInvocation.MyCommand.Path) { Split-Path -Parent $MyInvocation.MyCommand.Path }
                 else { $PWD.Path }
    $ExePath = Join-Path $ScriptDir "dist\steelseries.exe"
}

# Ensure WorkDir is always absolute (handles relative default path)
$WorkDir = if (Test-Path $ExePath) {
    Split-Path (Resolve-Path $ExePath).Path -Parent
} else {
    $parentPath = Split-Path $ExePath -Parent
    if ([System.IO.Path]::IsPathRooted($parentPath)) {
        $parentPath
    } else {
        Join-Path $PWD.Path $parentPath
    }
}
#endregion

#region Uninstall
if ($Uninstall) {
    $taskRemoved = Remove-ExistingTask -Name $TaskName
    Remove-LegacyLauncher -Dir $WorkDir

    if (-not $taskRemoved) {
        Write-Host "Nothing to uninstall: task not found" -ForegroundColor Yellow
    }
    exit 0
}
#endregion

#region Validate Executable
if (-not (Test-Path $ExePath)) {
    Write-Host "Error: Executable not found: $ExePath" -ForegroundColor Red
    Write-Host "Build first with: pyinstaller --onefile --name steelseries src/steelseries_oled/cli.py" -ForegroundColor Yellow
    exit 1
}

$ExePath = (Resolve-Path $ExePath).Path
$WorkDir = Split-Path $ExePath -Parent
#endregion

#region Install
# Remove existing task if present
if (Remove-ExistingTask -Name $TaskName -Silent) {
    Write-Host "Removed existing task" -ForegroundColor Yellow
}

# Clean up VBS launcher from previous versions
Remove-LegacyLauncher -Dir $WorkDir

# Create scheduled task that runs the exe directly
$Action = New-ScheduledTaskAction `
    -Execute $ExePath `
    -Argument "stats" `
    -WorkingDirectory $WorkDir

$Trigger = New-ScheduledTaskTrigger -AtLogon
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount $RestartCount `
    -RestartInterval (New-TimeSpan -Minutes $RestartIntervalMinutes) `
    -ExecutionTimeLimit 0 `
    -MultipleInstances IgnoreNew

try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -ErrorAction Stop | Out-Null
} catch {
    Write-Host "Error: Failed to create scheduled task: $_" -ForegroundColor Red
    Write-Host "Try running as Administrator if permission denied." -ForegroundColor Yellow
    exit 1
}

Write-Host "Created scheduled task: $TaskName" -ForegroundColor Green
Write-Host "  Executable: $ExePath" -ForegroundColor Cyan
Write-Host "  Trigger:    At logon" -ForegroundColor Cyan
Write-Host ""

if ($StartNow) {
    try {
        Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
        Write-Host "Task started." -ForegroundColor Green
    } catch {
        Write-Warning "Task created but failed to start: $_"
    }
} else {
    Write-Host "Commands:" -ForegroundColor White
    Write-Host "  Start now:  Start-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
    Write-Host "  Stop:       Stop-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
    Write-Host "  Status:     Get-ScheduledTask -TaskName $TaskName | Select State" -ForegroundColor Gray
    Write-Host "  Uninstall:  .\setup-autostart.ps1 -Uninstall" -ForegroundColor Gray
}
#endregion
