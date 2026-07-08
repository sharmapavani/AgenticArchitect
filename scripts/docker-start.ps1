#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed or not in PATH."
}

try {
    docker compose version | Out-Null
} catch {
    Write-Error "Docker Compose v2 is not available."
}

$EnvFile = Join-Path $Root "multiagentchat\.env"
$EnvExample = Join-Path $Root "multiagentchat\.env.example"

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Write-Host "Creating multiagentchat\.env from .env.example..."
        Copy-Item $EnvExample $EnvFile
        Write-Host "IMPORTANT: Edit multiagentchat\.env and set OPENAI_API_KEY before crew runs."
    } else {
        Write-Error "multiagentchat\.env.example not found."
    }
}

$Profile = $args[0]
if ($Profile -eq "observability") {
    Write-Host "Starting with observability profile..."
    docker compose --profile observability up --build -d
} else {
    docker compose up --build -d
}

Write-Host ""
Write-Host "Services starting. Validate with:"
Write-Host "  Invoke-WebRequest http://localhost:8000/health"
Write-Host "  Invoke-WebRequest http://localhost:3000/api/health"
Write-Host "  Start http://localhost:3000"
Write-Host ""
Write-Host "Logs: docker compose logs -f backend frontend"
