param(
    [string]$ExePath = "",
    [string]$OutDir = "",
    [string]$Algorithm = "SHA256"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

if (-not $ExePath) {
    $ExePath = Join-Path $scriptDir 'dist\Cleanroom\Cleanroom.exe'
}
if (-not $OutDir) {
    $OutDir = Join-Path $scriptDir 'dist'
}

if (-not (Test-Path $ExePath)) {
    Write-Error "Executable not found: $ExePath"
    exit 1
}

$bytes = [System.IO.File]::ReadAllBytes($ExePath)
$hashAlg = [System.Security.Cryptography.HashAlgorithm]::Create($Algorithm)
$hash = $hashAlg.ComputeHash($bytes)
$hex = ($hash | ForEach-Object { $_.ToString('x2') }) -join ''
$manifest = @{ exe = (Get-Item $ExePath).FullName; length = (Get-Item $ExePath).Length; algorithm = $Algorithm; hash = $hex; time = (Get-Date).ToString('o') }
$manifestPath = Join-Path $OutDir "artifact_manifest.json"
$manifest | ConvertTo-Json | Out-File -FilePath $manifestPath -Encoding utf8
Write-Host "Wrote manifest: $manifestPath"
Write-Host "Hash: $hex" -ForegroundColor Green
