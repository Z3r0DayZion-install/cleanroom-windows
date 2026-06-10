param(
    [string]$IssFile = "installer.iss"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$exe = Join-Path $scriptDir 'dist\Cleanroom.exe'
if (-not (Test-Path $exe)) {
    $exe = Join-Path $scriptDir 'dist\Cleanroom\Cleanroom.exe'
}
if (-not (Test-Path $exe)) {
    Write-Error "dist\Cleanroom.exe not found. Run build_exe.ps1 first."
    exit 1
}

# Locate the Inno Setup compiler
$candidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
)
$iscc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    $cmd = Get-Command iscc -ErrorAction SilentlyContinue
    if ($cmd) { $iscc = $cmd.Source }
}
if (-not $iscc) {
    Write-Error "Inno Setup (ISCC.exe) not found. Install it from https://jrsoftware.org/isinfo.php (or 'winget install JRSoftware.InnoSetup') and re-run."
    exit 1
}

Write-Host "Compiling installer with: $iscc"
& $iscc (Join-Path $scriptDir $IssFile)
if ($LASTEXITCODE -eq 0) {
    Write-Host "Installer built in dist\ (Cleanroom-Setup-*.exe)"
} else {
    Write-Error "Installer build failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
