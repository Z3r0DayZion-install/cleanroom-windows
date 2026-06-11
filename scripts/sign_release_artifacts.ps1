param(
    [string]$Version = ""
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$root = Split-Path -Parent $scriptDir

$pfxB64 = $env:SIGNING_CERT_BASE64
$pfxPass = $env:SIGNING_CERT_PASSWORD
if (-not $pfxB64) {
    Write-Host 'SIGNING_CERT_BASE64 not set - building unsigned release artifacts.'
    exit 0
}

$pfxPath = Join-Path $env:RUNNER_TEMP "cleanroom-sign.pfx"
[System.IO.File]::WriteAllBytes($pfxPath, [Convert]::FromBase64String($pfxB64))

$signScript = Join-Path $root 'sign_artifacts.ps1'
& $signScript -PfxPath $pfxPath -PfxPassword $pfxPass
$code = $LASTEXITCODE
Remove-Item -Force $pfxPath -ErrorAction SilentlyContinue
exit $code
