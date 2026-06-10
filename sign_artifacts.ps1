param(
    # Either a PFX file + password...
    [string]$PfxPath = "",
    [string]$PfxPassword = "",
    # ...or the thumbprint of a cert already in the user/machine store
    [string]$Thumbprint = "",
    [string]$TimestampUrl = "http://timestamp.digicert.com",
    # Create a throwaway self-signed cert (local testing only; SmartScreen
    # still warns — a real OV/EV certificate is required for that)
    [switch]$SelfSigned
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$targets = @(
    (Join-Path $scriptDir 'dist\Cleanroom\Cleanroom.exe'),
    (Join-Path $scriptDir 'dist\Cleanroom.exe'),
    (Get-ChildItem (Join-Path $scriptDir 'dist') -Filter 'Cleanroom-Setup-*.exe' -ErrorAction SilentlyContinue | ForEach-Object FullName)
) | Where-Object { $_ -and (Test-Path $_) }

if (-not $targets) {
    Write-Error "Nothing to sign. Build first (build_exe.ps1 / build_installer.ps1)."
    exit 1
}

# Locate signtool.exe (Windows SDK)
$signtool = Get-Command signtool -ErrorAction SilentlyContinue | ForEach-Object Source
if (-not $signtool) {
    $kits = "${env:ProgramFiles(x86)}\Windows Kits\10\bin"
    if (Test-Path $kits) {
        $signtool = Get-ChildItem $kits -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '\\x64\\' } |
            Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
    }
}
if (-not $signtool) {
    Write-Error "signtool.exe not found. Install the Windows 10/11 SDK (winget install Microsoft.WindowsSDK.10) and re-run."
    exit 1
}

if ($SelfSigned -and -not $Thumbprint -and -not $PfxPath) {
    Write-Host "Creating a self-signed code-signing certificate (CurrentUser\My)..."
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=Cleanroom (self-signed)" -CertStoreLocation Cert:\CurrentUser\My
    $Thumbprint = $cert.Thumbprint
    Write-Warning "Self-signed certs do NOT satisfy SmartScreen; use only for local testing."
}

$signArgs = @('sign', '/fd', 'SHA256', '/td', 'SHA256', '/tr', $TimestampUrl)
if ($PfxPath) {
    $signArgs += @('/f', $PfxPath)
    if ($PfxPassword) { $signArgs += @('/p', $PfxPassword) }
} elseif ($Thumbprint) {
    $signArgs += @('/sha1', $Thumbprint)
} else {
    Write-Error "Provide -PfxPath (+ -PfxPassword), -Thumbprint, or -SelfSigned."
    exit 1
}

$failed = 0
foreach ($t in $targets) {
    Write-Host "Signing $t"
    & $signtool @signArgs $t
    if ($LASTEXITCODE -ne 0) { $failed++ }
}
if ($failed) {
    Write-Error "$failed file(s) failed to sign."
    exit 1
}
Write-Host "All artifacts signed. Verify with: signtool verify /pa dist\Cleanroom\Cleanroom.exe"
