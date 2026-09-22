# Upload do instalador para o Vercel Blob (store do download publico).
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File upload_installer.ps1
#   powershell -ExecutionPolicy Bypass -File upload_installer.ps1 -Path "dist\Maouse-Setup-1.0.1.exe" -Name "Maouse-Setup-1.0.1.exe"
#
# O token e' lido de web\.env.local (BLOB_READ_WRITE_TOKEN) ou da variavel
# de ambiente com o mesmo nome. Depois do upload, confirma que a URL publica
# devolve HTTP 200 e mostra o tamanho servido.

param(
    [string]$Path = "dist\Maouse-Setup-1.0.0.exe",
    [string]$Name = "Maouse-Setup-1.0.0.exe"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path -LiteralPath $Path)) {
    Write-Error "Instalador nao encontrado: $Path"
    exit 1
}

# ── Token ──────────────────────────────────────────────────────────────
$token = $env:BLOB_READ_WRITE_TOKEN
if (-not $token -and (Test-Path "$root\web\.env.local")) {
    foreach ($line in Get-Content "$root\web\.env.local") {
        if ($line -match '^BLOB_READ_WRITE_TOKEN="?([^"]+)"?$') {
            $token = $Matches[1]
            break
        }
    }
}
if (-not $token) {
    Write-Error "BLOB_READ_WRITE_TOKEN nao encontrado (env ou web\.env.local)."
    exit 1
}

$full = (Resolve-Path -LiteralPath $Path).Path
$size = (Get-Item -LiteralPath $full).Length

Write-Host "[1/2] A enviar $Name ($([math]::Round($size/1MB,1)) MB) para o Vercel Blob ..."
$json = & curl.exe -sS -X POST "https://api.vercel.com/v3/blobs" `
    -H "Authorization: Bearer $token" `
    -F "file=@$full" `
    -F "path=$Name"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Falha no envio (curl exit $LASTEXITCODE): $json"
    exit 1
}

$result = $json | ConvertFrom-Json
if (-not $result.url) {
    Write-Error "Resposta inesperada do Blob: $json"
    exit 1
}
Write-Host "  URL: $($result.url)"

Write-Host "[2/2] A confirmar HTTP 200 ..."
try {
    $r = Invoke-WebRequest -Uri $result.url -Method Head -UseBasicParsing -TimeoutSec 30
    Write-Host "  OK: $($r.StatusCode)  |  $([math]::Round([int64]$r.Headers['Content-Length']/1MB,1)) MB"
} catch {
    Write-Warning "URL carregada mas HEAD falhou: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "Update NEXT_PUBLIC_DOWNLOAD_URL na Vercel com esta URL se mudar de nome:"
Write-Host "  npx vercel env add NEXT_PUBLIC_DOWNLOAD_URL production"