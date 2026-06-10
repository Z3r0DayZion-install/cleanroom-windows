param(
    [string]$TaskName = "CleanroomDaily",
    [string]$Time = "02:00",
    [ValidateSet('DAILY', 'WEEKLY')]
    [string]$Schedule = "DAILY",
    # Comma-separated weekday codes for WEEKLY schedules, e.g. "MON,WED,SUN"
    [string]$Days = "",
    # Path to Cleanroom.exe: schedules the self-contained exe (no Python needed)
    [string]$ExePath = "",
    [switch]$Dedup,
    [switch]$RunNow
)

if ($ExePath) {
    # Self-contained: the packaged exe runs the cleaner headlessly
    $action = "`"$ExePath`" --headless-clean"
    if ($Dedup) { $action += " --dedupe" }
} else {
    # Dev fallback: PowerShell wrapper that runs prune + cleaner via python
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $wrapper = Join-Path $scriptDir 'run_scheduled.ps1'
    $action = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$wrapper`""
    if ($Dedup) { $action += " -Dedupe" }
}

Write-Host "Creating scheduled task '$TaskName' ($Schedule at $Time) to run: $action"

$schtasksArgs = @('/Create', '/TN', $TaskName, '/TR', $action, '/SC', $Schedule, '/ST', $Time, '/F', '/RL', 'HIGHEST')
if ($Schedule -eq 'WEEKLY') {
    if (-not $Days) { $Days = 'SUN' }
    $schtasksArgs += @('/D', $Days)
}

$s = Start-Process -FilePath schtasks -ArgumentList $schtasksArgs -NoNewWindow -PassThru -Wait
if ($s.ExitCode -eq 0) {
    Write-Host "Scheduled task created successfully."
    if ($RunNow) {
        Write-Host "Running task now..."
        schtasks /Run /TN $TaskName
    }
} else {
    Write-Error "Failed to create scheduled task. ExitCode: $($s.ExitCode)"
    exit $s.ExitCode
}
