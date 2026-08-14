$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# Starts the API from the same configuration as the bot. Keep this window open
# while using the Vite dashboard in a separate terminal.
$health = $null
try { $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2 } catch { }
if ($health -and $health.ok) {
    Write-Host 'Dashboard API is already running at http://127.0.0.1:8000.'
    exit 0
}
if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 8000 is occupied by another process. Stop that process or configure a different API port.'
}
python -m uvicorn dashboard_api:app --host 127.0.0.1 --port 8000
