param(
    [string]$PythonExe = "python",
    [string]$ToolDir = (Split-Path -Parent $MyInvocation.MyCommand.Definition),
    [int]$PruneDays = 90,
    [switch]$Dedupe
)

Push-Location $ToolDir
Write-Host "Running prune_archive.py (dry-run by default unless PRUNE_APPLY env is set)"
$pruneApply = $env:CLEANROOM_PRUNE_APPLY
if ($pruneApply -and $pruneApply -eq '1') {
    & $PythonExe prune_archive.py --archive .\..\Downloads\cleanup_archive --days $PruneDays --apply
} else {
    & $PythonExe prune_archive.py --archive .\..\Downloads\cleanup_archive --days $PruneDays
}

Write-Host "Running main cleaner"
$cleanerArgs = @('main.py', '--config', '.\cleanup_config.yaml', '--apply', '--no-prompt')
if ($Dedupe) { $cleanerArgs += '--dedupe' }
& $PythonExe @cleanerArgs

Pop-Location
