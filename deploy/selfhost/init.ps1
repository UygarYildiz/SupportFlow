# Create .env with random secrets for a self-hosted SupportFlow (docs/SELF_HOSTING.md).
# Run from PowerShell:  .\init.ps1   (if blocked: powershell -ExecutionPolicy Bypass -File .\init.ps1)
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

if (Test-Path .env) {
    Write-Output '.env already exists; leaving it unchanged (delete it to start over).'
    Select-String -Path .env -Pattern '^SETUP_TOKEN=' | ForEach-Object { $_.Line }
    exit 0
}

function New-RandomHex([int]$bytes) {
    $buffer = New-Object byte[] $bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($buffer)
    $rng.Dispose()
    return -join ($buffer | ForEach-Object { $_.ToString('x2') })
}

$setupToken = New-RandomHex 12
$content = Get-Content .env.example | ForEach-Object {
    if ($_ -match '^POSTGRES_PASSWORD=') { "POSTGRES_PASSWORD=$(New-RandomHex 24)" }
    elseif ($_ -match '^JWT_SECRET_KEY=') { "JWT_SECRET_KEY=$(New-RandomHex 32)" }
    elseif ($_ -match '^SETUP_TOKEN=') { "SETUP_TOKEN=$setupToken" }
    else { $_ }
}
# UTF-8 without BOM: Docker Compose reads .env as plain text.
[System.IO.File]::WriteAllLines((Join-Path $PSScriptRoot '.env'), $content, (New-Object System.Text.UTF8Encoding $false))

Write-Output 'Created .env with random secrets.'
Write-Output ''
Write-Output "  Setup code: $setupToken"
Write-Output ''
Write-Output 'Next: docker compose up -d --build, then open http://localhost:8080'
